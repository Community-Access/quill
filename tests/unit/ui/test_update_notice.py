"""The one update dialog every app shows: notes, Update, Close.

Two things are asserted here that used to be true in QUILL and false in the
eight companion apps: that the dialog carries a *summary of what is new* rather
than a bare version number, and that the affirmative and escape buttons are
called **Update** and **Close** everywhere.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from quill.ui import update_notice


def test_markdown_release_body_is_flattened_for_speech():
    """A screen reader reads '## What's new' as two number signs. The notes go
    into the dialog as prose, not as punctuation."""
    summary = update_notice.summarize_release_notes("## What's new\n\n* Faster startup\n")
    assert "#" not in summary
    assert "Faster startup" in summary


def test_headings_and_rules_do_not_leave_a_line_of_dashes_to_read():
    """The flattener underlines headings; a reader says 'dash dash dash'."""
    summary = update_notice.summarize_release_notes(
        "# Title\n\n## What's new\n\n- Faster startup\n\n---\n\nEnd"
    )
    assert summary == "Title\n\nWhat's new\n\n- Faster startup\n\nEnd"


def test_a_release_with_no_body_says_so_rather_than_showing_nothing():
    """An empty notes box reads as a broken dialog."""
    assert update_notice.summarize_release_notes("   ") == update_notice.NO_NOTES


def test_a_changelog_of_every_commit_ever_is_shortened_and_says_it_was():
    raw = "\n".join(f"Fix number {n}" for n in range(500))
    summary = update_notice.summarize_release_notes(raw)
    assert summary.count("\n") < 500
    assert "full notes are on the release page" in summary


def test_blank_runs_collapse_so_arrowing_down_moves_through_content():
    summary = update_notice.summarize_release_notes("One\n\n\n\n\nTwo")
    assert summary == "One\n\nTwo"


def test_the_header_names_the_app_so_the_user_knows_which_window_asked():
    header = update_notice.update_header("Quill Radio", "3.0.0", "3.1.0", published_at="2026-09-12")
    assert "Quill Radio 3.1.0" in header
    assert "Current version: 3.0.0" in header
    assert "Published: 2026-09-12" in header
    assert "Stable" in header


def test_a_prerelease_says_which_channel_it_came_from():
    header = update_notice.update_header("QUILL", "1.0", "1.1", prerelease=True)
    assert "Beta / prerelease" in header


class _FakeWx:
    """Just enough wx for the dialog builder, recording what it was asked for."""

    ID_OK = 5100
    ID_CANCEL = 5101
    ID_IGNORE = 5102
    DEFAULT_DIALOG_STYLE = 1
    RESIZE_BORDER = 2
    EXPAND = LEFT = RIGHT = TOP = ALL = BOTTOM = VERTICAL = HORIZONTAL = 0
    TE_MULTILINE = TE_READONLY = TE_AUTO_URL = TE_RICH2 = 0
    EVT_BUTTON = object()

    def __init__(self) -> None:
        self.buttons: list[tuple[str, int]] = []
        self.notes = ""
        self.focused: list[str] = []

    # -- the widgets the dialog builds -------------------------------------

    def Dialog(self, _parent, *, title="", style=0):  # noqa: N802 - wx API shape
        return SimpleNamespace(
            SetSize=lambda _s: None,
            SetSizer=lambda _s: None,
            EndModal=lambda _r: None,
            Destroy=lambda: None,
            title=title,
        )

    def BoxSizer(self, _orient):  # noqa: N802 - wx API shape
        return SimpleNamespace(Add=lambda *a, **k: None, AddStretchSpacer=lambda: None)

    def StaticText(self, _parent, label=""):  # noqa: N802 - wx API shape
        return SimpleNamespace(label=label)

    def TextCtrl(self, _parent, value="", style=0, name=""):  # noqa: N802 - wx API shape
        self.notes = value
        return SimpleNamespace(
            SetName=lambda _n: None,
            SetHelpText=lambda _t: None,
            SetFocus=lambda: self.focused.append("notes"),
        )

    def Button(self, _parent, return_id, label=""):  # noqa: N802 - wx API shape
        self.buttons.append((label, return_id))
        return SimpleNamespace(Bind=lambda *a, **k: None, SetDefault=lambda: None)

    def CallAfter(self, func, *args, **kwargs):  # noqa: N802 - wx API shape
        func(*args, **kwargs)


@pytest.fixture
def fake_wx(monkeypatch):
    fake = _FakeWx()
    monkeypatch.setattr(update_notice, "apply_modal_ids", lambda *a, **k: None)
    return fake


def _release(**kw):
    return SimpleNamespace(
        version=kw.get("version", "2.0.0"),
        notes=kw.get("notes", "* Something changed"),
        published_at=kw.get("published_at", ""),
        prerelease=kw.get("prerelease", False),
    )


def test_a_companion_app_offers_exactly_update_and_close(fake_wx):
    """No Skip button outside QUILL: nowhere to record the answer."""
    update_notice.show_update_available(
        None,
        app_name="Quill Weather",
        current_version="1.0.0",
        release=_release(),
        show_modal_dialog=lambda _d, _t: _FakeWx.ID_CANCEL,
        wx_module=fake_wx,
    )
    assert [label for label, _id in fake_wx.buttons] == ["Close", "Update"]


def test_the_dialog_shows_what_changed(fake_wx):
    update_notice.show_update_available(
        None,
        app_name="QuillLite",
        current_version="1.0.0",
        release=_release(notes="## Fixed\n\n* The status bar reads back again"),
        show_modal_dialog=lambda _d, _t: _FakeWx.ID_CANCEL,
        wx_module=fake_wx,
    )
    assert "The status bar reads back again" in fake_wx.notes


def test_focus_lands_on_the_notes_not_on_a_button(fake_wx):
    """A dialog that opens on its default button reads the button and stops."""
    update_notice.show_update_available(
        None,
        app_name="QuillLite",
        current_version="1.0.0",
        release=_release(),
        show_modal_dialog=lambda _d, _t: _FakeWx.ID_CANCEL,
        wx_module=fake_wx,
    )
    assert fake_wx.focused == ["notes"]


def test_pressing_update_says_update(fake_wx):
    assert (
        update_notice.show_update_available(
            None,
            app_name="QuillLite",
            current_version="1.0.0",
            release=_release(),
            show_modal_dialog=lambda _d, _t: _FakeWx.ID_OK,
            wx_module=fake_wx,
        )
        == "update"
    )


def test_pressing_close_says_close(fake_wx):
    assert (
        update_notice.show_update_available(
            None,
            app_name="QuillLite",
            current_version="1.0.0",
            release=_release(),
            show_modal_dialog=lambda _d, _t: _FakeWx.ID_CANCEL,
            wx_module=fake_wx,
        )
        == "close"
    )


def test_quill_alone_gets_the_skip_button(fake_wx):
    choice = update_notice.show_update_available(
        None,
        app_name="QUILL",
        current_version="1.0.0",
        release=_release(),
        show_modal_dialog=lambda _d, _t: _FakeWx.ID_IGNORE,
        allow_skip=True,
        wx_module=fake_wx,
    )
    assert [label for label, _id in fake_wx.buttons] == ["Close", "Skip this version", "Update"]
    assert choice == "skip"


def test_skip_is_not_reachable_when_the_host_cannot_record_it(fake_wx):
    """An app with no skip button must never be told the user skipped."""
    choice = update_notice.show_update_available(
        None,
        app_name="Quill Cast",
        current_version="1.0.0",
        release=_release(),
        show_modal_dialog=lambda _d, _t: _FakeWx.ID_IGNORE,
        wx_module=fake_wx,
    )
    assert choice == "close"


def test_the_available_version_is_announced_once(fake_wx):
    said: list[str] = []
    update_notice.show_update_available(
        None,
        app_name="QuillLite",
        current_version="1.0.0",
        release=_release(version="1.2.0"),
        show_modal_dialog=lambda _d, _t: _FakeWx.ID_CANCEL,
        announce=said.append,
        wx_module=fake_wx,
    )
    assert said == ["Update available: 1.2.0"]
