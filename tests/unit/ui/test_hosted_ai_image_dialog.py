"""Ask About an Image: the picture and the question, checked before OK."""

from __future__ import annotations

import pytest

wx = pytest.importorskip("wx")

from quill.ui.hosted_ai_image import AskImageDialog, image_wildcard  # noqa: E402


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


def test_the_wildcard_offers_the_formats_the_plan_takes() -> None:
    wildcard = image_wildcard()
    for suffix in (".png", ".jpg", ".jpeg", ".webp", ".gif"):
        assert f"*{suffix}" in wildcard


def test_ok_is_refused_until_there_is_an_image_file(wx_app, tmp_path) -> None:
    said = []
    dialog = AskImageDialog(None, announce=said.append)
    try:
        assert dialog.problem() == "Choose an image file first."
        dialog.path.SetValue(str(tmp_path / "missing.png"))
        assert "no file" in dialog.problem()
        text = tmp_path / "notes.txt"
        text.write_text("x")
        dialog.path.SetValue(str(text))
        assert "JPEG, PNG, WebP or GIF" in dialog.problem()
        picture = tmp_path / "pic.png"
        picture.write_bytes(b"not really checked here")
        dialog.path.SetValue(f'"{picture}"')
        assert dialog.problem() == ""
        dialog.question.SetValue("  What is it?  ")
        path, question = dialog.chosen()
        assert path == picture
        assert question == "What is it?"
    finally:
        dialog.Destroy()


def test_browse_fills_the_path_and_moves_on_to_the_question(wx_app, tmp_path) -> None:
    picture = tmp_path / "pic.jpg"
    dialog = AskImageDialog(None, choose_file=lambda: str(picture))
    try:
        dialog._on_browse()
        assert dialog.path.GetValue() == str(picture)
    finally:
        dialog.Destroy()


def test_a_cancelled_browse_changes_nothing(wx_app) -> None:
    dialog = AskImageDialog(None, initial_path="C:/kept.png", choose_file=lambda: "")
    try:
        dialog._on_browse()
        assert dialog.path.GetValue() == "C:/kept.png"
    finally:
        dialog.Destroy()
