"""Mark Language, In Short, the statement, the Palette Report and the reading level (9.7-9.12)."""

from __future__ import annotations

from quill.core.wordpress import local as lc
from quill.ui import wordpress_check_commands as wcc

API = "/wp-json/wp/v2"


def _open_doc(wp, text, fmt="markdown"):
    copy = lc.WorkingCopy(
        site_id="radio",
        kind="post",
        local_id="",
        remote_id=8,
        title="Festival",
        text=text,
        text_format=fmt,
        status="draft",
    )
    path = wp.local.write_document(copy)
    wp.host.path = path
    wp.host.text = text
    return copy


# --------------------------------------------------------------------------- #
# Mark Language


def test_mark_language_needs_a_wordpress_document(wp) -> None:
    wp.cmd_mark_language()
    assert "This is not a WordPress document" in wp.host.said


def test_mark_language_wraps_the_selection(wp, wp_dialogs) -> None:
    _open_doc(wp, "She said bonjour to us.")
    wp.host.selection = (9, 16)
    wp_dialogs.answer("ask_text", "French")
    wp.cmd_mark_language()
    assert wp.host.text == 'She said <span lang="fr">bonjour</span> to us.'
    assert wp.host.announced[-1] == "The selection is marked as French."
    wp.host.selection = (0, 3)
    wp.cmd_mark_language()  # cancelled: the last language is offered, nothing changes
    assert wp_dialogs.asked("ask_text")[-1]["value"] == "fr"
    assert wp.host.text.startswith("She said")


def test_mark_language_marks_the_whole_page_in_block_form(wp, wp_dialogs) -> None:
    _open_doc(wp, "<!-- wp:paragraph -->\n<p>Hola</p>\n<!-- /wp:paragraph -->", fmt="html")
    wp_dialogs.answer("ask_text", "es")
    wp.cmd_mark_language()
    assert '<p><span lang="es">Hola</span></p>' in wp.host.text
    assert wp.host.announced[-1] == "The whole page is marked as Spanish."


def test_mark_language_refuses_what_is_not_a_language(wp, wp_dialogs) -> None:
    _open_doc(wp, "Text")
    wp_dialogs.answer("ask_text", "Klingon please")
    wp.cmd_mark_language()
    assert "does not know 'Klingon please' as a language" in wp.host.said
    assert wp.host.text == "Text"


def test_mark_language_on_an_empty_page(wp, wp_dialogs) -> None:
    _open_doc(wp, "")
    wp_dialogs.answer("ask_text", "fr")
    wp.cmd_mark_language()
    assert wp.host.announced[-1] == "There is nothing on the page to mark yet."


# --------------------------------------------------------------------------- #
# In Short


class FakeService:
    def __init__(self, answer="Two short sentences. Plain ones.", error=""):
        self.answer = answer
        self.error = error
        self.prompts: list[str] = []

    def ask(self, feature, prompt, chunks, *, on_done, on_error, requires):
        self.prompts.append(prompt)
        if self.error:
            on_error(self.error)
        else:
            on_done(self.answer, None)


class FakeEditor:
    def __init__(self, service, *, ready=True):
        self.service = service
        self.ready = ready

    def _ai_ready(self):
        return self.ready

    def _ai_capable(self, _what):
        return True

    def _ai_service(self):
        return self.service


def test_in_short_goes_on_top_as_one_change_with_a_version_kept(wp) -> None:
    copy = _open_doc(wp, "The festival runs all weekend.\n")
    wp.host.caret = 20
    service = FakeService()
    wp.host.ai_editor = lambda: FakeEditor(service)
    wp.cmd_in_short()
    assert "The festival runs all weekend." in service.prompts[0]
    assert wp.host.text == (
        "**In short:** Two short sentences. Plain ones.\n\nThe festival runs all weekend.\n"
    )
    assert wp.host.caret == 0
    assert "In Short is at the top" in wp.host.announced[-1]
    assert wp.local.versions(copy.key)[0].reason == lc.REASON_BEFORE_AI


def test_in_short_without_ai_in_the_window(wp) -> None:
    _open_doc(wp, "Text.")
    wp.cmd_in_short()
    assert wp.host.announced[-1] == "AI help is not available in this window."
    wp.host.ai_editor = lambda: object()
    wp.cmd_in_short()
    assert wp.host.announced[-1] == "AI help is not available in this window."


def test_in_short_when_ai_is_not_ready_sends_nothing(wp) -> None:
    _open_doc(wp, "Text.")
    service = FakeService()
    wp.host.ai_editor = lambda: FakeEditor(service, ready=False)
    wp.cmd_in_short()
    assert service.prompts == [] and wp.host.text == "Text."


def test_in_short_failures_and_empty_answers_change_nothing(wp) -> None:
    _open_doc(wp, "Text.")
    wp.host.ai_editor = lambda: FakeEditor(FakeService(error="The AI is busy. Try again soon."))
    wp.cmd_in_short()
    assert wp.host.announced[-1] == "The AI is busy. Try again soon."
    wp.host.ai_editor = lambda: FakeEditor(FakeService(answer="  "))
    wp.cmd_in_short()
    assert "sent back nothing" in wp.host.announced[-1]
    assert wp.host.text == "Text."


def test_in_short_on_an_empty_page(wp) -> None:
    _open_doc(wp, "<!-- wp:paragraph -->\n<p></p>\n<!-- /wp:paragraph -->", fmt="html")
    wp.host.ai_editor = lambda: FakeEditor(FakeService())
    wp.cmd_in_short()
    assert wp.host.announced[-1] == "There is nothing to summarise yet."


# --------------------------------------------------------------------------- #
# Accessibility statement


def test_statement_opens_a_new_page_draft_and_sends_nothing(wp, wp_site, wp_dialogs) -> None:
    wp_site.on("GET", f"{API}/settings", {"email": "admin@radio.example"})
    wp_dialogs.answer("ask_text", lambda **kw: kw["value"])
    wp.cmd_accessibility_statement()
    assert wp.host.opened, "the draft should open in the editor"
    assert "admin@radio.example" in wp.host.text and "WCAG) 2.2 at level AA" in wp.host.text
    assert "nothing is sent until you choose" in wp.host.announced[-1]
    assert [r.get_method() for r in wp_site.requests] == ["GET"]
    copy = wp.local.copy_for_path(wp.host.current_path())
    assert copy.kind == "page" and copy.remote_id == 0


def test_statement_offers_no_email_when_the_account_cannot_see_it(wp, wp_dialogs) -> None:
    wp.cmd_accessibility_statement()
    assert wp_dialogs.asked("ask_text")[-1]["value"] == ""
    assert wp.host.opened == []


# --------------------------------------------------------------------------- #
# Palette Report


GLOBAL_STYLES = {
    "settings": {
        "color": {
            "palette": {
                "theme": [
                    {"slug": "base", "name": "Base", "color": "#ffffff"},
                    {"slug": "contrast", "name": "Contrast", "color": "#111111"},
                    {"slug": "pale", "name": "Pale yellow", "color": "#fff8c4"},
                    {"slug": "fade", "name": "Fade", "color": "linear-gradient(red, blue)"},
                ]
            }
        }
    },
    "styles": {"color": {"background": "var:preset|color|base"}},
}


def test_palette_report_says_the_count_and_shows_every_pairing(wp, wp_site, wp_dialogs) -> None:
    wp_site.on("GET", f"{API}/themes", [{"name": {"raw": "Twenty"}, "stylesheet": "tt5"}])
    wp_site.on("GET", f"{API}/global-styles/themes/tt5", GLOBAL_STYLES)
    wp.cmd_palette_report()
    said = wp.host.announced[-1]
    assert said.startswith("Twenty on Community Radio: 6 pairings, ")
    text = wp_dialogs.reports[-1]["text"]
    assert "Contrast (" in text and "too faint for text" in text
    assert "linear-gradient" not in text


def test_palette_report_with_no_theme_to_read(wp) -> None:
    wp.cmd_palette_report()
    assert (
        wp.host.announced[-1]
        == "QUILL could not read a colour palette from Community Radio's theme."
    )


# --------------------------------------------------------------------------- #
# The reading-level line for Properties


def test_reading_level_line_for_markdown_and_html() -> None:
    line = wcc.reading_level_line("The cat sat. The dog ran.")
    assert line.startswith("Reading level: about ") and line.endswith("3 words per sentence")
    html = "<!-- wp:paragraph --><p>The cat sat.</p><!-- /wp:paragraph -->"
    assert wcc.reading_level_line(html).endswith("3 words per sentence")
    assert wcc.reading_level_line("") == "Reading level: not enough text to judge"
