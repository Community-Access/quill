"""Small QuillLite defects, each of which cost a listener something specific.

Grouped here rather than scattered because they share a shape: the code did
something reasonable and *said* something that was not true, or said nothing at
all -- which for somebody who cannot glance at the screen is the same as a key
that is not bound. Every one of them is a row in bad.md section 6.
"""

from __future__ import annotations

# --------------------------------------------------------------------------- #
# H7. The MDI child-close key nothing bound
# --------------------------------------------------------------------------- #


def test_ctrl_f4_closes_the_document_like_ctrl_w(lite_window) -> None:
    """Windows has closed an MDI child with Ctrl+F4 since 3.1, and QuillLite is
    MDI. Nothing bound it, so the key did nothing -- and the two comments that
    mentioned Alt+F4 disagreed about what that one did (bad.md H7)."""
    win = lite_window("hello")
    win.cmd_close_mdi()
    assert win.closed == 1


# --------------------------------------------------------------------------- #
# R13. Describe Formatting in a Markdown document
# --------------------------------------------------------------------------- #


def test_describe_reads_markdown_bold_rather_than_denying_it(lite_window) -> None:
    """It answered "Plain text" with the caret inside ``**bold**``, which is not
    a description of the formatting but a denial that there is any."""
    win = lite_window("a **strong word** here", cursor=6, mode="plain")
    win.set_document_language("markdown", announce=False)
    win.cmd_describe()
    assert "bold" in win.announcements[-1].lower()


def test_describe_names_the_heading_level_in_markdown(lite_window) -> None:
    win = lite_window("## Section two\n\nbody\n", cursor=6, mode="plain")
    win.set_document_language("markdown", announce=False)
    win.cmd_describe()
    assert "heading" in win.announcements[-1].lower()


def test_describe_still_says_plain_text_where_there_is_none(lite_window) -> None:
    win = lite_window("just words", cursor=4, mode="plain")
    win.set_document_language("plain", announce=False)
    win.cmd_describe()
    assert win.announcements[-1] == "Plain text"


def test_moving_a_section_knows_the_document_is_html(lite_window) -> None:
    """move_section was told "markdown" whatever the document was, so it looked
    for hashes an HTML file will never contain and said "not in a section" about
    a section (bad.md R13)."""
    html = "<h1>One</h1>\n<p>first</p>\n<h1>Two</h1>\n<p>second</p>\n"
    win = lite_window(html, cursor=html.index("Two"), mode="plain")
    win.set_document_language("html", announce=False)
    win.cmd_move_section_up()
    assert win.control.GetValue().index("<h1>Two</h1>") < win.control.GetValue().index(
        "<h1>One</h1>"
    )


# --------------------------------------------------------------------------- #
# A5. The announcement throttle
# --------------------------------------------------------------------------- #


def test_the_voice_says_everything_when_the_throttle_is_off() -> None:
    from quill.apps.lite_voice import ScreenReaderVoice

    voice = ScreenReaderVoice()
    said: list[str] = []
    voice._reader_running = lambda: True  # type: ignore[method-assign]
    voice._engine = type("E", (), {"announce": lambda _s, text, **_k: said.append(text)})()
    for message in ("one", "two", "three"):
        voice.speak(message)
    assert said == ["one", "two", "three"]


def test_the_throttle_drops_what_comes_too_soon() -> None:
    """A held key that announces per repeat floods the reader, and the only
    remedy a listener had was to switch speech off (bad.md A5). The status bar
    is written before the voice is reached, so nothing is lost that cannot be
    read back."""
    from quill.apps.lite_voice import ScreenReaderVoice

    voice = ScreenReaderVoice()
    said: list[str] = []
    voice._reader_running = lambda: True  # type: ignore[method-assign]
    voice._engine = type("E", (), {"announce": lambda _s, text, **_k: said.append(text)})()
    voice.throttle_ms = 60_000
    for message in ("one", "two", "three"):
        voice.speak(message)
    assert said == ["one"]


def test_the_app_hands_the_voice_the_setting(lite_window) -> None:
    win = lite_window("hello")
    win.app.settings.announcement_throttle_ms = 250
    assert win.app.settings.announcement_throttle_ms == 250


# --------------------------------------------------------------------------- #
# F13 / PR2. Page setup outliving the session
# --------------------------------------------------------------------------- #


def test_the_stored_margins_survive_a_round_trip(tmp_path) -> None:
    from quill.core.lite import settings as settings_mod

    path = tmp_path / "settings.json"
    settings = settings_mod.Settings()
    settings.print_paper_id = 1
    settings.print_landscape = True
    settings.print_margins_mm = [20, 25, 20, 25]
    settings_mod.save(settings, path)

    back = settings_mod.load(path)
    assert back.print_paper_id == 1
    assert back.print_landscape is True
    assert back.print_margins_mm == [20, 25, 20, 25]


def test_a_nonsense_margin_list_falls_back_to_the_defaults() -> None:
    from quill.core.lite.settings import Settings

    settings = Settings()
    settings.print_margins_mm = [15, 15]
    assert settings.normalized().print_margins_mm == [15, 15, 15, 15]

    settings.print_margins_mm = [15, 15, 15, -4]
    assert settings.normalized().print_margins_mm == [15, 15, 15, 15]


# --------------------------------------------------------------------------- #
# F7. Two dialogs that were honest about plain text and silent about rich
# --------------------------------------------------------------------------- #


def test_earlier_versions_warns_that_a_rich_restore_loses_formatting(
    lite_window, lite_dialogs, tmp_path
) -> None:
    """A backup stores the text and none of the runs, so restoring one into a
    rich document replaces formatted text with flat text. The dialog offered the
    rows and said nothing about it (bad.md F7)."""
    path = tmp_path / "notes.rtf"
    path.write_text("body", encoding="utf-8")
    win = lite_window("body", cursor=0, mode="rich")
    win.path = path

    from quill.core.lite import backups as backups_mod

    backups_mod.write_backup(path, "an earlier body")
    win.cmd_browse_backups()
    assert "loses the formatting" in lite_dialogs.kwargs_for("choose_from_rows")["help_text"]


def test_the_encoding_dialog_is_refused_in_rich_text(lite_window, lite_dialogs) -> None:
    """It dirtied the document, announced "Saving as UTF-16, CRLF" and changed
    nothing at all: _write_rtf reads neither field (bad.md F7)."""
    win = lite_window("body", cursor=0, mode="rich")
    win.cmd_file_format()
    assert "rich text document has its own format" in win.announcements[-1]
    assert lite_dialogs.names() == []
    assert win.modified is False
