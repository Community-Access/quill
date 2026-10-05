"""Locked -> hidden: the YouTube account features wait on Google's approval.

``future.youtube_oauth`` is ``released=False``, so a public build locks it off.
Every surface that acts as the listener's YouTube account must then be absent
-- not disabled, not explained -- even when a Google client *is* baked into
the build, because a client is baked before Google approves it. The gate is
the feature flag, never ``youtube_oauth.available()`` alone.
"""

from __future__ import annotations

import pytest

from quill.core.auth.token_bundle import TokenBundle
from quill.core.features import FeatureManager
from quill.core.radio import youtube_oauth as oauth

wx = pytest.importorskip("wx")


def _public_build(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("QUILL_DEV_BUILD", raising=False)


class _Tasks:
    def submit(self, *_a, **_k) -> None:
        return None


class _App:
    """The Radio app frame as the account surfaces see it."""

    def __init__(self, features) -> None:
        self.said: list[str] = []
        self._announce = self.said.append
        self._task_manager = _Tasks()
        self.features = features
        self._safe_mode = False
        self.frame = None


class _On:
    def is_enabled(self, _feature_id: str) -> bool:
        return True


@pytest.fixture
def baked_and_signed_in(monkeypatch):
    """A client baked into the build and a stored session: the worst case."""
    monkeypatch.setattr(oauth, "available", lambda: True)
    monkeypatch.setattr(
        oauth,
        "load_tokens",
        lambda: TokenBundle(
            access_token="AT", refresh_token="RT", expires_at=9e12, scope=oauth.SCOPE
        ),
    )
    monkeypatch.delenv("QUILL_SAFE_MODE", raising=False)


@pytest.fixture
def locked_app(monkeypatch, baked_and_signed_in):
    _public_build(monkeypatch)
    features = FeatureManager()
    features.grant_product_features({"core.radio"})  # what Quill Radio does
    assert features.is_enabled("future.youtube_oauth") is False
    return _App(features)


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


def test_the_flag_is_locked_off_and_hidden_from_customize_features(monkeypatch) -> None:
    from quill.core.feature_catalog import FEATURE_DEFINITIONS

    _public_build(monkeypatch)
    # Manage Individual Features omits every is_locked_off feature.
    assert FEATURE_DEFINITIONS["future.youtube_oauth"].is_locked_off is True


def test_can_sign_in_follows_the_flag_not_the_baked_client(locked_app) -> None:
    from quill.ui.radio.youtube_account_ui import can_sign_in

    assert can_sign_in(locked_app) is False
    assert can_sign_in(_App(_On())) is True


def test_connect_and_disconnect_rows_are_not_in_the_station_menu(locked_app) -> None:
    from quill.apps.radio_youtube_oauth_menu import add_youtube_oauth_menu_items

    class _Menu:
        def __init__(self) -> None:
            self.rows: list[str] = []

        def Append(self, _id, label) -> None:  # noqa: N802 - wx shape
            self.rows.append(label)

    menu = _Menu()
    add_youtube_oauth_menu_items(locked_app, menu, wx)
    assert menu.rows == []


def _comments_window(app):
    from quill.ui.radio.youtube_comments_window import YouTubeCommentsWindow

    frame = wx.Frame(None)
    window = YouTubeCommentsWindow(
        frame,
        video_title="A video",
        page_url="https://www.youtube.com/watch?v=abcdefghijk",
        task_manager=_Tasks(),
        announce=lambda _t: None,
        account_app=app,
    )
    return frame, window


def _labels(window) -> list[str]:
    return [child.GetLabel() for child in window._panel.GetChildren()]


def test_comment_write_buttons_are_absent_when_locked(wx_app, locked_app) -> None:
    frame, window = _comments_window(locked_app)
    try:
        assert window._account_buttons == ()
        labels = _labels(window)
        assert not any("Reply" in label or "Delete My" in label for label in labels)
        assert "&Add a Comment..." not in labels
    finally:
        window.frame.Destroy()
        frame.Destroy()


def test_comment_write_buttons_appear_when_the_flag_is_on(wx_app, baked_and_signed_in) -> None:
    frame, window = _comments_window(_App(_On()))
    try:
        assert len(window._account_buttons) == 3
    finally:
        window.frame.Destroy()
        frame.Destroy()


def test_comment_write_buttons_need_an_app_at_all(wx_app, baked_and_signed_in) -> None:
    frame, window = _comments_window(None)
    try:
        assert window._account_buttons == ()
    finally:
        window.frame.Destroy()
        frame.Destroy()


def _video_window(app):
    from quill.ui.radio.youtube_video_window import YouTubeVideoWindow

    frame = wx.Frame(None)
    window = YouTubeVideoWindow(
        frame, host=app, station=None, page_url="https://www.youtube.com/watch?v=abcdefghijk"
    )
    return frame, window


def test_video_window_account_buttons_are_absent_when_locked(wx_app, locked_app) -> None:
    from quill.ui.radio.youtube_video_window import ACCOUNT_BUTTONS

    frame, window = _video_window(locked_app)
    try:
        for attr in ACCOUNT_BUTTONS:
            assert not hasattr(window, attr), attr
        labels = _labels(window)
        for gone in ("&Like", "D&islike", "Add to &Playlist...", "Add a &Comment..."):
            assert gone not in labels
        # What works without Google stays.
        assert "Live C&hat..." in labels and "&Save Audio..." in labels
    finally:
        window.frame.Destroy()
        frame.Destroy()


def test_video_window_account_buttons_appear_when_the_flag_is_on(
    wx_app, baked_and_signed_in
) -> None:
    from quill.ui.radio.youtube_video_window import ACCOUNT_BUTTONS

    frame, window = _video_window(_App(_On()))
    try:
        for attr in ACCOUNT_BUTTONS:
            assert hasattr(window, attr), attr
    finally:
        window.frame.Destroy()
        frame.Destroy()


def test_live_chat_opens_without_a_send_box_when_locked(wx_app, locked_app, monkeypatch) -> None:
    from quill.ui.radio import youtube_comments_ui, youtube_live_chat_ui
    from quill.ui.radio import youtube_live_chat_window as chat_window

    made: dict = {}

    class _Window:
        def __init__(self, _parent, **kwargs) -> None:
            made.update(kwargs)
            self.frame = None

        def start(self) -> None:
            pass

    monkeypatch.setattr(chat_window, "YouTubeLiveChatWindow", _Window)
    monkeypatch.setattr(youtube_comments_ui, "_show_as_peer", lambda *_a, **_k: None)

    class _Station:
        stream_url = "https://www.youtube.com/watch?v=abcdefghijk"
        name = "A stream"

    youtube_live_chat_ui.open_for_station(locked_app, _Station())
    assert made["can_send"] is False and made["send"] is None


def test_subscribe_uses_the_confirm_page_when_locked(locked_app) -> None:
    from quill.ui.radio import youtube_row_account

    opened: list[bool] = []
    youtube_row_account.subscribe(
        locked_app, None, ["https://www.youtube.com/@x"], lambda: opened.append(True)
    )
    assert opened == [True]


def test_the_published_f1_reference_does_not_describe_them() -> None:
    from quill.tools.build_help_reference import generate

    text = generate()
    for phrase in (
        "Connect YouTube Account",
        "Delete My Comment",
        "Alt+R Reply",
        "send it as your YouTube account",
        "act as your connected",
        "the send box",
    ):
        assert phrase not in text, phrase
