r"""The Format rows follow the document, not the moment the window was built.

Reported: "I pasted text into QUILL Lite that was markdown and then used
Alt+Shift+F to change to markdown mode. The keys are grayed out in the format
menu for markdown logic, like promoting and demoting headings, Alt+Shift+Left
and Right arrow."

``tests/unit/apps/test_lite_format_gating.py`` already asserts that the gating
*table* matches what each command does, and it passed throughout. The table was
never the problem. The sweep that applies it ran twice -- once when the bar was
built, and once from ``EVT_MENU_OPEN`` on the document frame -- and a QUILL Lite
document is a ``wx.MDIChildFrame`` whose menu bar wxMSW merges into the shell.
The menu-open event is delivered to the parent. So the sweep ran exactly once,
against a document that was plain at the time, and every markup row stayed
dimmed for the life of the window however many times the language changed.

A dimmed row's accelerator does not fire, so this was eighteen dead keys with
nothing said about any of them -- the failure GATE-13's sibling rule names: an
app that under-delivers silently gets filed as "it doesn't work", eventually.

What these tests pin down is the part the gating test cannot see: that the
sweep is re-run **by the change itself**, so the answer is right whether or not
a menu is ever opened.
"""

from __future__ import annotations

import pytest

from quill.apps.lite_window_markup import MARKUP_COMMANDS
from quill.core.lite.format_kinds import FORMAT_COMMAND_KINDS

#: The rows the report was about: everything a Markdown document can express.
STRUCTURE = (
    "cmd_promote_heading",
    "cmd_demote_heading",
    "cmd_move_section_up",
    "cmd_move_section_down",
)
EMPHASIS = ("cmd_bold", "cmd_italic", "cmd_underline")
HEADINGS = tuple(f"cmd_heading_{level}" for level in range(7)) + ("cmd_normal_text",)


class _Item:
    """Enough of ``wx.MenuItem`` for the enable sweep to act on."""

    def __init__(self) -> None:
        self.enabled = True

    def Enable(self, value: bool) -> None:  # noqa: N802 - wx spelling
        self.enabled = bool(value)


def _wire_menu(window):
    """Give *window* the registry and the real sweep a document frame has.

    The sweep is the shipped
    :meth:`~quill.apps.lite_window_menus.DocumentMenuMixin.sync_menu_state`,
    bound to the stub -- not a stand-in for it. A stand-in here could only
    prove that *something* was called, and what has to be true is that the
    shipped sweep reaches the shipped rows.
    """
    from quill.apps.lite_window_menus import DocumentMenuMixin

    window._menu_items = {handler: _Item() for handler in (*FORMAT_COMMAND_KINDS, *MARKUP_COMMANDS)}
    window._sync_enabled_items = lambda: DocumentMenuMixin._sync_enabled_items(window)
    window.sync_menu_state = lambda: DocumentMenuMixin.sync_menu_state(window)
    # The build-time sweep, which is the only one that used to happen.
    window.sync_menu_state()
    return window


def _live(window, handler: str) -> bool:
    return window._menu_items[handler].enabled


@pytest.fixture
def wired(lite_window):
    """An untitled plain document with a menu, as File > New leaves one."""
    window = lite_window("# Heading one\n\nSome text\n")
    window.path = None
    window._language_override = ""
    return _wire_menu(window)


def test_a_new_plain_document_dims_the_markup_rows(wired) -> None:
    # The starting state, and the one that was correct all along. Asserted so a
    # fix that simply enabled everything would fail here rather than look green.
    for handler in (*STRUCTURE, *EMPHASIS, *HEADINGS):
        assert not _live(wired, handler), f"{handler} is live in a plain document"


def test_switching_to_markdown_lights_the_markdown_rows(wired) -> None:
    # The report, exactly: Alt+Shift+F once, from plain, lands on Markdown.
    wired.cmd_switch_document_kind()
    assert wired.document_language() == "markdown"
    for handler in (*STRUCTURE, *EMPHASIS, *HEADINGS, "cmd_cycle_list_style"):
        assert _live(wired, handler), (
            f"{handler} is still dimmed in a Markdown document. Its accelerator "
            "will not fire, and nothing says why."
        )
    assert _live(wired, "cmd_insert_markdown_tag")
    assert not _live(wired, "cmd_insert_html_tag")


def test_ringing_on_to_html_moves_the_picker_and_keeps_the_structure(wired) -> None:
    wired.cmd_switch_document_kind()  # markdown
    wired.cmd_switch_document_kind()  # html
    assert wired.document_language() == "html"
    # Headings are ``<h2>`` as readily as ``##``: quill.core.heading_levels has
    # always spelled both, so the structure rows stay live.
    for handler in (*STRUCTURE, *EMPHASIS, *HEADINGS):
        assert _live(wired, handler), f"{handler} is dimmed in an HTML document"
    assert _live(wired, "cmd_insert_html_tag")
    assert not _live(wired, "cmd_insert_markdown_tag")
    # The list cycle has no HTML spelling, which the gating table measured
    # rather than assumed. It is the one markup row that goes dark here.
    assert not _live(wired, "cmd_cycle_list_style")


def test_choosing_a_language_directly_lights_the_rows_too(wired) -> None:
    # The Language cell and Ctrl+Alt+F6 reach set_document_language without
    # going through the ring, and have to arrive at the same window state.
    wired.set_document_language("markdown", announce=False)
    assert all(_live(wired, handler) for handler in STRUCTURE)
    wired.set_document_language("plain", announce=False)
    assert not any(_live(wired, handler) for handler in STRUCTURE)


def test_going_back_to_plain_dims_them_again(wired) -> None:
    wired.set_document_language("markdown", announce=False)
    assert _live(wired, "cmd_promote_heading")
    wired.set_document_language("plain", announce=False)
    assert not _live(wired, "cmd_promote_heading"), (
        "a row left live in a plain document is the other half of the bug: it "
        "advertises a key that can only answer 'this document has no formatting'"
    )


def test_the_rich_only_rows_are_the_mirror_image(wired) -> None:
    rich_only = ("cmd_align_left", "cmd_spacing_double", "cmd_grow_font")
    wired.set_document_language("markdown", announce=False)
    for handler in rich_only:
        assert not _live(wired, handler), f"{handler} is markup-free; Markdown cannot say it"
    # And the two that keep the Format menu worth opening in any document.
    assert _live(wired, "cmd_switch_document_kind")
    assert _live(wired, "cmd_set_language")


def test_saving_an_untitled_document_as_markdown_lights_the_rows(wired, tmp_path) -> None:
    # No override in play: the *name* is what decides the language, and Save As
    # is the moment an untitled document first has one.
    assert not _live(wired, "cmd_promote_heading")
    assert wired.save(tmp_path / "notes.md") is True
    assert wired.document_language() == "markdown"
    assert _live(wired, "cmd_promote_heading"), (
        "Save As gave the document a Markdown name and the menu did not notice"
    )


def test_opening_a_markdown_file_lights_the_rows(wired, tmp_path) -> None:
    target = tmp_path / "opened.md"
    target.write_text("# Heading one\n", encoding="utf-8")
    assert not _live(wired, "cmd_promote_heading")
    assert wired.load(target) is True
    assert _live(wired, "cmd_promote_heading")


def test_the_shell_hands_the_menu_to_the_document_that_built_it() -> None:
    """The MDI half: the event arrives at the parent, and has to be passed on.

    Unbound against a stand-in rather than a real ``wx.MDIParentFrame``: what
    has to be true is that the shell asks its *active child* to re-sweep, and a
    real MDI frame adds a window on screen to prove it.
    """
    from quill.apps.lite_shell import QuillLiteShell

    class _Child:
        def __init__(self) -> None:
            self.synced = 0

        def sync_menu_state(self) -> None:
            self.synced += 1

    class _Event:
        def __init__(self) -> None:
            self.skipped = 0

        def Skip(self) -> None:  # noqa: N802 - wx spelling
            self.skipped += 1

    class _Shell:
        def __init__(self, child) -> None:
            self._child = child

        def GetActiveChild(self):  # noqa: N802 - wx spelling
            return self._child

    child = _Child()
    event = _Event()
    QuillLiteShell._on_menu_open(_Shell(child), event)
    assert child.synced == 1
    # Skipped, or the child's own binding and anything else watching the bar
    # never see the event.
    assert event.skipped == 1


def test_the_shell_survives_a_menu_opened_with_no_document() -> None:
    """The placeholder bar. ``GetActiveChild`` answers None, and that is fine."""
    from quill.apps.lite_shell import QuillLiteShell

    class _Event:
        skipped = 0

        def Skip(self) -> None:  # noqa: N802 - wx spelling
            type(self).skipped += 1

    class _Shell:
        def GetActiveChild(self):  # noqa: N802 - wx spelling
            return None

    QuillLiteShell._on_menu_open(_Shell(), _Event())
