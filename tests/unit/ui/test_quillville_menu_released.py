"""The QuillVille menu only offers apps that have shipped a public release."""

from __future__ import annotations

from types import SimpleNamespace

from quill.ui import quillville_menu as qv


class _FakeMenu:
    def __init__(self) -> None:
        self.labels: list[str] = []

    def Append(self, _id: object, label: str) -> None:  # noqa: N802 - wx shape
        self.labels.append(label)


class _FakeWx:
    _next = 1000

    def Menu(self):  # noqa: N802 - wx shape
        return _FakeMenu()

    def NewIdRef(self):  # noqa: N802 - wx shape
        _FakeWx._next += 1
        return _FakeWx._next

    EVT_MENU = object()


def _build(exclude: str) -> list[str]:
    wx = _FakeWx()
    frame = SimpleNamespace(Bind=lambda *a, **k: None)
    menu = qv.build_quillville_menu(
        wx, frame, on_launch=lambda _k: None, exclude=exclude, retain=lambda _i: None
    )
    return menu.labels


def test_unreleased_apps_are_not_offered() -> None:
    # Quill Cast and Audio Studio are built but not released yet.
    assert "cast" not in qv.RELEASED_APPS
    assert "studio" not in qv.RELEASED_APPS
    labels = _build(exclude="quill")
    joined = " ".join(labels)
    assert "Quill Cast" not in joined
    assert "Audio Studio" not in joined


def test_released_siblings_are_offered_and_self_is_excluded() -> None:
    labels = _build(exclude="radio")  # from Quill Radio
    assert "Open QUILL" in labels
    assert "Open Quill Weather" in labels
    assert "Open Quill Radio" not in labels  # self excluded
