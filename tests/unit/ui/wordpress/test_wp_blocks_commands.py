"""File > WordPress > Blocks, behaviourally: insert, move, the Blocks window, settings, preview."""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.wordpress import local as lc
from quill.core.wordpress.blocks import parse, serialize
from quill.core.wordpress.fences import check_markdown
from quill.ui import wordpress_block_dialogs as bdlg
from quill.ui import wordpress_dialogs as dlg

API = "/wp-json/wp/v2"

MARKDOWN = (
    "Welcome to the station.\n\n"
    "## Times\n\n"
    "::: columns\n::: column\nMorning sessions.\n::: column\nEvening sessions.\n"
    "::: end columns\n\n"
    "- tea\n- cake\n"
)
P1 = "<!-- wp:paragraph -->\n<p>First words.</p>\n<!-- /wp:paragraph -->"
H2 = '<!-- wp:heading -->\n<h2 class="wp-block-heading">A heading</h2>\n<!-- /wp:heading -->'
HTML = f'{P1}\n\n{H2}\n\n<!-- wp:latest-posts {{"postsToShow":2}} /-->\n'

STYLES = {
    "settings": {
        "color": {
            "palette": [
                {"slug": "base", "name": "Base", "color": "#ffffff"},
                {"slug": "accent", "name": "Accent", "color": "#2f5d50"},
                {"slug": "pale", "name": "Pale yellow", "color": "#fff8c4"},
            ]
        },
        "typography": {"fontSizes": [{"slug": "large", "name": "Large", "size": "1.4rem"}]},
    },
    "styles": {"color": {"background": "#ffffff", "text": "#000000"}},
}


def _doc(wp: Any, text: str, fmt: str = "markdown", islands: dict[str, str] | None = None) -> Any:
    copy = lc.WorkingCopy(
        site_id="radio",
        kind="page",
        local_id=lc.new_local_id(),
        title="Schedule",
        text=text,
        text_format=fmt,
        properties={"islands": dict(islands or {})},
    )
    wp.host.open_path(wp.local.write_document(copy))
    return copy


class FormScript(list):
    """Scripted block forms: ``answer`` queues a dict (or None to cancel); calls are kept."""

    def __init__(self) -> None:
        super().__init__()
        self.answers: list[Any] = []

    def answer(self, value: Any) -> None:
        self.answers.append(value)

    def __call__(self, _parent: Any, _show_modal: Any, **kwargs: Any) -> Any:
        self.append(kwargs)
        return self.answers.pop(0) if self.answers else None


@pytest.fixture
def form(monkeypatch: pytest.MonkeyPatch) -> FormScript:
    script = FormScript()
    monkeypatch.setattr(bdlg, "ask_fields", script)
    return script


def _islands(wp: Any) -> dict[str, str]:
    copy = wp.local.copy_for_path(wp.host.current_path())
    return copy.properties.get("islands") or {}


# --------------------------------------------------------------------------- #
# outside a WordPress document


@pytest.mark.parametrize(
    "run",
    [
        lambda w: w.cmd_insert_block(),
        lambda w: w.cmd_next_block(),
        lambda w: w.cmd_previous_block(),
        lambda w: w.cmd_where_am_i(),
        lambda w: w.cmd_blocks_window(),
        lambda w: w.cmd_block_settings(),
        lambda w: w.cmd_preview_blocks(),
    ],
)
def test_every_block_command_needs_a_wordpress_document(wp, wp_site, run) -> None:
    run(wp)
    assert "This is not a WordPress document" in wp.host.said
    assert wp_site.requests == []


# --------------------------------------------------------------------------- #
# Next Block, Previous Block, Where Am I


def test_next_block_moves_and_says_the_block_and_its_position(wp) -> None:
    _doc(wp, MARKDOWN)
    wp.cmd_next_block()
    assert wp.host.caret == MARKDOWN.index("## Times")
    assert wp.host.announced[-1] == "Heading level 2 block, 2 of 8: Times"
    wp.cmd_next_block()
    assert wp.host.announced[-1] == "Columns block, 3 of 8: 2 columns"


def test_next_block_at_the_end_says_so(wp) -> None:
    _doc(wp, MARKDOWN)
    wp.host.caret = len(MARKDOWN) - 3
    wp.cmd_next_block()
    assert wp.host.announced[-1] == "No more blocks after this one."


def test_previous_block_at_the_start_says_so(wp) -> None:
    _doc(wp, MARKDOWN)
    wp.cmd_previous_block()
    assert wp.host.announced[-1] == "No blocks before this one."
    wp.host.caret = MARKDOWN.index("Evening") + 2
    wp.cmd_previous_block()
    assert wp.host.caret == MARKDOWN.index("Evening")
    assert wp.host.announced[-1] == "Paragraph block, 7 of 8: Evening sessions."


def test_an_empty_document_has_no_blocks(wp) -> None:
    _doc(wp, "")
    wp.cmd_next_block()
    wp.cmd_where_am_i()
    wp.cmd_blocks_window()
    assert (
        wp.host.announced == ["This document has no blocks yet. Insert one with Insert Block."] * 3
    )


def test_where_am_i_says_the_nesting(wp) -> None:
    _doc(wp, MARKDOWN)
    wp.host.caret = MARKDOWN.index("Morning") + 1
    wp.cmd_where_am_i()
    assert wp.host.announced[-1] == (
        "Paragraph block: Morning sessions., inside column 1 of Columns."
    )


def test_html_documents_move_through_real_block_markup(wp) -> None:
    _doc(wp, HTML, "html")
    wp.cmd_next_block()
    wp.cmd_next_block()
    assert wp.host.caret == HTML.index("<!-- wp:latest-posts")
    assert wp.host.announced[-1] == "Latest posts block, 3 of 3"


# --------------------------------------------------------------------------- #
# Insert Block


def test_insert_block_lists_core_blocks_patterns_and_synced_patterns(
    wp, wp_site, wp_dialogs
) -> None:
    _doc(wp, MARKDOWN)
    wp_site.on(
        "GET",
        f"{API}/block-types",
        [{"name": "acme/events", "title": "Events", "is_dynamic": True, "attributes": {}}],
    )
    wp_site.on(
        "GET",
        f"{API}/block-patterns/patterns",
        [{"name": "radio/staff", "title": "Staff profile", "content": P1}],
    )
    wp_site.on("GET", f"{API}/blocks", [{"id": 9, "title": {"raw": "Footer"}}])
    wp.cmd_insert_block()
    rows = wp_dialogs.window["rows"]
    assert rows[0].startswith("Paragraph")
    assert "Events" in rows
    assert "Staff profile, pattern" in rows
    assert "Footer, synced pattern" in rows
    narrowed = wp_dialogs.window["on_filter"]("but")
    assert narrowed == ["Buttons: A button that links somewhere."]


def test_insert_a_button_writes_a_fence_after_the_current_block(wp, wp_dialogs, form) -> None:
    _doc(wp, MARKDOWN)
    wp.host.caret = 3
    wp.cmd_insert_block()
    rows = wp_dialogs.window["rows"]
    wp_dialogs.window["on_filter"]("button")
    form.answer({"text": "Book a session", "url": "https://radio.example/book", "new_tab": False})
    assert wp_dialogs.press("&Insert", 0) is dlg.CLOSE
    assert rows
    assert form[0]["title"] == "Insert Buttons"
    expected = '::: button "Book a session" https://radio.example/book'
    assert wp.host.text.startswith(f"Welcome to the station.\n\n{expected}\n\n## Times")
    assert wp.host.caret == wp.host.text.index(expected)
    assert wp.host.announced[-1] == "Buttons inserted."


def test_cancelling_the_form_inserts_nothing(wp, wp_dialogs, form) -> None:
    _doc(wp, MARKDOWN)
    wp.cmd_insert_block()
    assert wp_dialogs.press("&Insert", 0) is None
    assert wp.host.text == MARKDOWN


def test_insert_a_synced_pattern_in_markdown_keeps_it_as_an_island(wp, wp_site, wp_dialogs) -> None:
    _doc(wp, MARKDOWN)
    wp.host.caret = len(MARKDOWN)
    wp_site.on("GET", f"{API}/blocks", [{"id": 9, "title": {"raw": "Footer"}}])
    wp.cmd_insert_block()
    index = wp_dialogs.window["rows"].index("Footer, synced pattern")
    wp_dialogs.press("&Insert", index)
    assert wp.host.text.endswith("- cake\n\n::: block core/block island-1\n")
    assert _islands(wp) == {"island-1": '<!-- wp:block {"ref":9} /-->'}
    assert check_markdown(wp.host.text, _islands(wp)) == []


def test_insert_in_an_html_document_writes_block_markup(wp, wp_dialogs, form) -> None:
    _doc(wp, HTML, "html")
    wp.host.caret = 5
    wp.cmd_insert_block()
    form.answer({"text": "New words"})
    wp_dialogs.press("&Insert", 0)
    assert wp.host.text.startswith(
        f"{P1}\n\n<!-- wp:paragraph -->\n<p>New words</p>\n<!-- /wp:paragraph -->\n\n{H2}"
    )
    assert serialize(parse(wp.host.text)) == wp.host.text


# --------------------------------------------------------------------------- #
# The Blocks window


def test_blocks_window_lists_every_block_with_its_nesting(wp, wp_dialogs) -> None:
    _doc(wp, MARKDOWN)
    wp.cmd_blocks_window()
    rows = wp_dialogs.window["rows"]
    assert rows[0] == "Paragraph block: Welcome to the station."
    assert rows[3] == "Column block: Morning sessions., inside Columns"
    assert rows[4] == "Paragraph block: Morning sessions., inside Column"
    labels = [a.label for a in wp_dialogs.window["actions"]]
    letters = [lab[lab.index("&") + 1].lower() for lab in labels] + ["b"]
    assert len(letters) == len(set(letters))


def test_go_to_closes_and_puts_the_caret_on_the_block(wp, wp_dialogs) -> None:
    _doc(wp, MARKDOWN)
    wp.cmd_blocks_window()
    assert wp_dialogs.press("&Go To", 1) is dlg.CLOSE
    assert wp.host.caret == MARKDOWN.index("## Times")


def test_move_up_and_down_are_single_replacements(wp, wp_dialogs) -> None:
    _doc(wp, MARKDOWN)
    wp.cmd_blocks_window()
    rows = wp_dialogs.press("Move &Up", 1)
    assert wp.host.text.startswith("## Times\n\nWelcome to the station.\n\n::: columns")
    assert rows[0].startswith("Heading")
    assert wp.host.announced[-1] == "Moved up."
    wp_dialogs.press("Move Do&wn", 0)
    assert wp.host.text == MARKDOWN
    assert wp_dialogs.press("Move &Up", 0) is None
    assert wp.host.announced[-1] == "This is already the first block here."


def test_duplicate_and_remove_with_a_named_confirmation(wp, wp_dialogs) -> None:
    _doc(wp, MARKDOWN)
    wp.cmd_blocks_window()
    wp_dialogs.press("&Duplicate", 1)
    assert wp.host.text.count("## Times") == 2
    assert wp_dialogs.press("&Remove...", 1) is None
    assert wp.host.text.count("## Times") == 2
    asked = wp_dialogs.asked("confirm")[-1]
    assert asked["yes_label"] == "Remove Block"
    assert "Heading level 2 block: Times" in asked["message"]
    wp_dialogs.answer("confirm", True)
    wp_dialogs.press("&Remove...", 1)
    assert wp.host.text == MARKDOWN
    assert wp.host.announced[-1] == "Block removed."


def test_change_to_asks_what_and_changes_it(wp, wp_dialogs) -> None:
    _doc(wp, MARKDOWN)
    wp.cmd_blocks_window()
    wp_dialogs.answer("ask_choice", 0)
    wp_dialogs.press("&Change To...", 1)
    assert wp_dialogs.asked("ask_choice")[-1]["rows"][0] == "Paragraph"
    assert "\n\nTimes\n\n" in wp.host.text
    assert wp.host.announced[-1] == "Changed to Paragraph."


def test_change_to_on_a_block_with_no_changes(wp, wp_dialogs) -> None:
    _doc(wp, MARKDOWN)
    wp.cmd_blocks_window()
    wp_dialogs.press("&Change To...", 2)
    assert wp.host.announced[-1] == "QUILL cannot change this kind of block to another."


def test_group_and_ungroup(wp, wp_dialogs) -> None:
    _doc(wp, MARKDOWN)
    wp.cmd_blocks_window()
    rows = wp_dialogs.press("Gr&oup", 0)
    assert wp.host.text.startswith("::: group\nWelcome to the station.\n::: end group\n\n## Times")
    assert rows[0].startswith("Group block")
    wp_dialogs.press("U&ngroup", 0)
    assert wp.host.text == MARKDOWN
    assert wp_dialogs.press("U&ngroup", 0) is None
    assert wp.host.announced[-1] == "Only a Group block can be ungrouped."


# --------------------------------------------------------------------------- #
# Block Settings


def _theme(wp_site: Any) -> None:
    wp_site.on("GET", f"{API}/themes", [{"stylesheet": "radio-theme"}])
    wp_site.on("GET", f"{API}/global-styles/themes/radio-theme", STYLES)


def test_block_settings_in_html_writes_colours_and_warns_on_contrast(wp, wp_site, form) -> None:
    _doc(wp, HTML, "html")
    _theme(wp_site)
    wp.host.caret = 5
    form.answer({"align": None, "textColor": "pale", "backgroundColor": None, "fontSize": "large"})
    wp.cmd_block_settings()
    rows = next(f for f in form[0]["fields"] if f.key == "textColor").choices
    assert any(r.startswith("Accent (dark green)") and r.endswith("passes") for r in rows)
    assert wp.host.text.startswith(
        '<!-- wp:paragraph {"textColor":"pale","fontSize":"large"} -->\n'
        '<p class="has-pale-color has-text-color has-large-font-size">First words.</p>'
    )
    assert wp.host.text.endswith(f'\n\n{H2}\n\n<!-- wp:latest-posts {{"postsToShow":2}} /-->\n')
    said = wp.host.announced[-1]
    assert said.startswith("Block settings changed. The text and background are 1")
    assert "too faint for text" in said


def test_block_settings_cancel_changes_nothing(wp, wp_site, form) -> None:
    _doc(wp, HTML, "html")
    _theme(wp_site)
    wp.host.caret = 5
    wp.cmd_block_settings()
    assert wp.host.text == HTML


def test_block_settings_without_the_theme_still_offers_the_rest(wp, form) -> None:
    _doc(wp, HTML, "html")
    wp.host.caret = HTML.index("latest-posts") + 2
    form.answer({"postsToShow": "4"})
    wp.cmd_block_settings()
    assert "did not share its theme's colours" in form[0]["purpose"]
    assert '<!-- wp:latest-posts {"postsToShow":4} /-->' in wp.host.text
    assert wp.host.announced[-1] == "Block settings changed."


def test_block_settings_outside_a_block(wp) -> None:
    _doc(wp, "One\n\n\n\nTwo\n")
    wp.host.caret = 5
    wp.cmd_block_settings()
    assert wp.host.announced[-1].startswith("The caret is not in a block.")


def test_markdown_settings_ask_before_protecting_the_block(wp, wp_site, wp_dialogs, form) -> None:
    _doc(wp, MARKDOWN)
    _theme(wp_site)
    form.answer({"textColor": "accent"})
    wp.cmd_block_settings()
    assert wp_dialogs.asked("confirm")[-1]["yes_label"] == "Make Protected Block"
    assert wp.host.text == MARKDOWN
    form.answer({"textColor": "accent"})
    wp_dialogs.answer("confirm", True)
    wp.cmd_block_settings()
    assert wp.host.text.startswith("::: block core/paragraph island-1\n\n## Times")
    assert "has-accent-color" in _islands(wp)["island-1"]
    assert check_markdown(wp.host.text, _islands(wp)) == []


# --------------------------------------------------------------------------- #
# Preview Blocks


def test_preview_renders_dynamic_blocks_through_the_site(wp, wp_site, wp_dialogs) -> None:
    _doc(wp, HTML, "html")
    wp_site.on(
        "POST",
        f"{API}/block-renderer/core/latest-posts",
        {"rendered": '<ul><li><a href="/a">Spring fair</a></li></ul>'},
    )
    wp.cmd_preview_blocks()
    sent = wp_site.sent("POST", f"{API}/block-renderer/core/latest-posts")
    assert wp_site.body(sent[0]) == {"attributes": {"postsToShow": 2}}
    assert "context=edit" in sent[0].full_url
    report = wp_dialogs.reports[-1]
    assert report["text"].splitlines() == [
        "First words.",
        "Heading level 2: A heading",
        "- Spring fair",
    ]
    assert all(r.get_method() != "PUT" for r in wp_site.requests)


def test_preview_says_what_the_site_could_not_show(wp, wp_dialogs) -> None:
    _doc(wp, HTML, "html")
    wp.cmd_preview_blocks()
    assert "the site could not show this" in wp_dialogs.reports[-1]["text"]
    assert wp.host.announced[-1].startswith("Community Radio could not show 1 block: Latest posts")


def test_preview_of_markdown_sends_nothing_for_static_blocks(wp, wp_site, wp_dialogs) -> None:
    _doc(wp, MARKDOWN)
    wp.cmd_preview_blocks()
    assert wp_site.requests == []
    assert wp_dialogs.reports[-1]["text"].splitlines()[:2] == [
        "Welcome to the station.",
        "Heading level 2: Times",
    ]
