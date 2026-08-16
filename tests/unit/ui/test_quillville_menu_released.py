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
    # Every item carries a numbered accelerator (the house rule that a menu
    # item always shows a way to reach it), so compare on the name alone.
    names = [label.split(chr(9))[0] for label in labels]
    assert "Open QUILL" in names
    assert "Open Quill Weather" in names
    assert "Open Quill Radio" not in names  # self excluded
    # ...and the keys are there, numbered in menu order.
    assert [label.split(chr(9))[1] for label in labels][:2] == [
        "Ctrl+Alt+Shift+1",
        "Ctrl+Alt+Shift+2",
    ]


def test_an_app_can_leave_a_sibling_off_its_own_menu(monkeypatch) -> None:
    """Quill Radio ships 3.0 without Inkwell on its QuillVille menu.

    Not by un-releasing Inkwell -- it stays on every other app's menu. A
    listener opening a radio app has no reason to be offered a text expander,
    and a menu item that opens one is a promise that release did not mean to
    make.
    """
    from quill.ui import quillville_menu

    monkeypatch.setattr(quillville_menu, "is_app_released", lambda _key: True)
    offered: list[str] = []

    class _Menu:
        def Append(self, _id, label):
            offered.append(label)

    class _Wx:
        Menu = _Menu
        EVT_MENU = object()

        @staticmethod
        def NewIdRef():
            return object()

    class _Frame:
        def Bind(self, *_args, **_kwargs):
            return None

    quillville_menu.build_quillville_menu(
        _Wx,
        _Frame(),
        lambda _key: None,
        exclude="radio",
        retain=lambda _id: None,
        also_exclude=("inkwell",),
    )
    assert not any("Inkwell" in label for label in offered)
    # The rest of the family is untouched.
    assert any("QUILL" in label for label in offered)
