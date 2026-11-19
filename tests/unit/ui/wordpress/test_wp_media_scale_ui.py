"""Edit Picture's last row: change the original here and send it back (complete.md 2.3)."""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("wx")
pytest.importorskip("PIL")

from quill.core.wordpress import media_tools as mt  # noqa: E402
from quill.core.wordpress.workbench_rows import WbRow  # noqa: E402
from quill.ui import wordpress_dialogs as dlg  # noqa: E402
from quill.ui import wordpress_workbench_dialogs as wdlg  # noqa: E402
from tests.unit.ui.wordpress.test_wp_workbench_lists import SITE  # noqa: E402
from tests.unit.ui.wordpress.test_wp_workbench_lists import bench as _bench  # noqa: E402

bench = _bench


def _jpeg() -> bytes:
    from PIL import Image

    out = io.BytesIO()
    Image.new("RGB", (400, 300), (10, 20, 30)).save(out, format="JPEG")
    return out.getvalue()


def test_scale_previews_the_sizes_then_hands_the_file_to_replace_file(bench, monkeypatch) -> None:
    picture = WbRow(
        "media", SITE, "9", {"title": "Hall"}, "",
        raw={"source_url": "https://radio.example/uploads/hall.jpg"},
    )  # fmt: skip
    monkeypatch.setattr(dlg, "ask_text", lambda *_a, **_k: "200 wide")
    monkeypatch.setattr(
        mt,
        "download_file",
        lambda *_a, **_k: mt.Downloaded("hall.jpg", _jpeg(), "image/jpeg", "radio.example"),
    )
    shown: list[dict[str, Any]] = []
    monkeypatch.setattr(wdlg, "ask_preview", lambda *_a, **k: shown.append(k) or True)
    handed: list[tuple[WbRow, Path, Any]] = []
    monkeypatch.setattr(
        bench.provider,
        "replace_with",
        lambda row, path, after=None: handed.append((row, path, after)),
    )
    bench.api._opener, bench.api.timeout = None, 30.0  # the fake site's, for the download
    bench.provider.scale_on_this_computer(picture)
    assert shown[0]["summary"].startswith("Hall, scaled to 200 pixels wide.")
    assert shown[0]["lines"][0].startswith("Before: 400 by 300")
    ((row, path, after),) = handed
    assert row is picture and path.name == "hall.jpg" and callable(after)
    from PIL import Image

    assert Image.open(path).size == (200, 150)
