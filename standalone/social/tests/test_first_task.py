"""The demo timeline is marked as a demo where it is met (FUX-09).

A new install gets a local demo account so the app works at once. It was
explained only inside F1 help, so the first timeline read like a real network.
While the demo is the only account, launch says it is a demo on this computer
and names Add Account with its key; with a real account it says only "ready".
"""

from __future__ import annotations

import pytest

wx = pytest.importorskip("wx")


@pytest.fixture
def frame(tmp_path, monkeypatch):
    monkeypatch.setenv("QUILLSOCIAL_DATA", str(tmp_path / "data"))
    try:
        application = wx.App()
    except Exception:  # pragma: no cover - no display
        pytest.skip("wx cannot initialize in this environment")
    from quill_social.ui.app import SocialFrame

    f = SocialFrame()
    yield f
    f.Destroy()
    application.Destroy()


DEMO = (
    "QUILL Social ready. Demo timeline only. Add Account (Ctrl+Shift+A) connects Mastodon "
    "or Bluesky."
)


def test_with_only_the_demo_launch_says_it_is_a_demo_and_how_to_connect(frame) -> None:
    assert frame._ready_sentence() == DEMO
    assert frame.GetTitle().endswith("(demo)")  # what the screen reader reads first


def test_with_a_real_account_launch_says_only_ready(frame) -> None:
    from dataclasses import replace

    demo = frame.store.list_accounts()[0]
    frame.store.put_account(replace(demo, account_id="acct_real", network="mastodon"))
    assert frame._ready_sentence() == "QUILL Social ready."
