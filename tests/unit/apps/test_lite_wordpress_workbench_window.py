"""QUILL Lite opens the same WordPress Workbench window QUILL does (WP-R-024).

Tools > WordPress > Open WordPress Workbench in a QUILL Lite window runs the
shared ``WordPressCommands.cmd_workbench`` through Lite's own host, and the
window that opens is QUILL's: the same provider on the same shared frame, with
the same tree, actions and menu. Nothing here is Lite's own implementation
(test_lite_wordpress.py checks the adapter only hands off).
"""

from __future__ import annotations

from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.apps.lite_window_wordpress import DocumentWordPressMixin  # noqa: E402
from quill.apps.lite_window_wordpress_host import LiteWordPressHost  # noqa: E402
from quill.core.wordpress import sites as st  # noqa: E402
from quill.ui import wordpress_workbench_window as window  # noqa: E402
from quill.ui.wordpress_commands import WordPressCommands  # noqa: E402


class _LiteWindow(DocumentWordPressMixin):
    def __init__(self, frame: Any) -> None:
        self.frame = frame
        self.app = None
        self.path = None
        self.said: list[str] = []

    def _announce(self, text: str) -> None:
        self.said.append(text)


@pytest.fixture
def lite(wx_session_app, tmp_path, monkeypatch):
    monkeypatch.setattr(window, "_OPEN", {})
    frame = wx.Frame(None)
    win = _LiteWindow(frame)
    win._wordpress_commands = WordPressCommands(LiteWordPressHost(frame), data_dir=tmp_path)
    store = st.SiteStore([st.SiteProfile("s1", "Radio", "https://radio.example", "jeff")], "s1")
    st.save_sites(store, tmp_path)
    monkeypatch.setattr(window.WordPressWorkbenchProvider, "start", lambda self: None)
    yield win
    for opened in list(window._OPEN.values()):
        opened.frame.Destroy()
    frame.Destroy()


def test_lite_opens_quills_workbench_window_with_its_sites(lite) -> None:
    lite.cmd_wp_workbench()
    opened = window._OPEN["wordpress"]
    provider = opened.provider
    assert isinstance(provider, window.WordPressWorkbenchProvider)
    assert provider.commands is lite._wordpress_commands
    assert provider.tree is window.WORDPRESS_TREE and provider.menu is window.WINDOW_MENU
    assert list(provider.instances("site")) == ["Radio"]
    # A second time brings the same window forward, at the place it was left.
    here = opened.current
    lite.cmd_wp_workbench()
    assert window._OPEN["wordpress"] is opened and opened.current == here
