"""Social's exports end with what is now true (FUX-04).

Export OPML said "Exported 3 feed(s) to OPML." without saying where the file
went; Send to QUILL read a whole path aloud and raised in silence when the
write failed. Now OPML names the file and its folder, and Send to QUILL names
the folder and says when it could not write.
"""

from __future__ import annotations

from pathlib import Path

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
    said: list[str] = []
    monkeypatch.setattr(f.announcer, "say", lambda text, *a, **k: said.append(text))
    monkeypatch.setattr(f.announcer, "error", lambda text: said.append(text))
    f.said = said
    yield f
    f.Destroy()
    application.Destroy()


def test_opml_export_names_the_file_and_its_folder(frame, tmp_path: Path) -> None:
    target = tmp_path / "Downloads" / "feeds.opml"
    target.parent.mkdir()
    assert frame._write_opml(str(target), "<opml/>", 3) is True
    assert target.read_text(encoding="utf-8") == "<opml/>"
    assert frame.said == ["Exported 3 feeds to feeds.opml in Downloads."]


def test_one_feed_is_one_feed(frame, tmp_path: Path) -> None:
    frame._write_opml(str(tmp_path / "one.opml"), "<opml/>", 1)
    assert frame.said == [f"Exported 1 feed to one.opml in {tmp_path.name}."]


def test_send_to_quill_that_could_not_write_says_so(frame, monkeypatch) -> None:
    from quill_social.model import SocialItem

    item = SocialItem(network="rss", account_id="a", remote_id="r1")
    monkeypatch.setattr(frame, "_current_item", lambda: item)
    monkeypatch.setattr(frame.store, "list_items", lambda **_k: [item])
    shown: list[str] = []
    monkeypatch.setattr(frame, "_show_text", lambda title, text: shown.append(title))

    def refuse(self, *_a, **_k):
        raise PermissionError(13, "Permission denied", "C:/x/y.md")

    monkeypatch.setattr(Path, "write_text", refuse)
    frame.cmd_send_to_quill()
    assert frame.said == ["Could not save the thread for QUILL: Permission denied."]
    assert shown == []


def test_send_to_quill_names_the_folder_not_the_whole_path(frame, monkeypatch) -> None:
    from quill_social.model import SocialItem

    item = SocialItem(network="rss", account_id="a", remote_id="r1")
    monkeypatch.setattr(frame, "_current_item", lambda: item)
    monkeypatch.setattr(frame.store, "list_items", lambda **_k: [item])
    monkeypatch.setattr(frame, "_show_text", lambda title, text: None)
    frame.cmd_send_to_quill()
    assert frame.said == ["Saved the thread for QUILL in exports."]
    assert (frame.data_dir / "exports" / f"{item.item_id}.md").exists()
