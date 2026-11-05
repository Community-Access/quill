# ruff: noqa: E501 -- fixtures are exact WordPress markup, kept whole.
"""Block Settings with the theme's names and contrast, and the preview readout (8.4, 8.5, 9.7)."""

from __future__ import annotations

from quill.core.wordpress import block_preview as bp
from quill.core.wordpress import block_settings as bset
from quill.core.wordpress.api import WordPressApiError
from quill.core.wordpress.blocks import parse, serialize

GLOBAL_STYLES = {
    "settings": {
        "color": {
            "palette": {
                "theme": [
                    {"slug": "base", "name": "Base", "color": "#ffffff"},
                    {"slug": "contrast", "name": "Contrast", "color": "#111111"},
                    {"slug": "accent", "name": "Accent", "color": "#2f5d50"},
                    {"slug": "pale", "name": "Pale yellow", "color": "#fff8c4"},
                ],
                "default": [{"slug": "vivid-red", "name": "Vivid red", "color": "#cf2e2e"}],
            },
            "defaultPalette": False,
        },
        "typography": {
            "fontSizes": {"theme": [{"slug": "large", "name": "Large", "size": "1.375rem"}]},
            "defaultFontSizes": False,
        },
        "layout": {"contentSize": "650px", "wideSize": "1200px"},
    },
    "styles": {"color": {"background": "var:preset|color|base", "text": "var(--wp--preset--color--contrast)"}},
}  # fmt: skip

PARAGRAPH = "<!-- wp:paragraph -->\n<p>Doors open at nine.</p>\n<!-- /wp:paragraph -->"


def _block(markup: str = PARAGRAPH):
    return next(b for b in parse(markup) if not b.freeform)


def test_presets_come_from_the_theme_by_name() -> None:
    presets = bset.parse_presets(GLOBAL_STYLES)
    assert [p.name for p in presets.colours] == ["Base", "Contrast", "Accent", "Pale yellow"]
    assert [p.name for p in presets.font_sizes] == ["Large"]
    assert presets.background == "#ffffff"
    assert presets.text == "#111111"
    assert presets.wide is True


def test_a_theme_without_a_wide_size_offers_no_wide_or_full() -> None:
    styles = {"settings": {"layout": {"contentSize": "650px"}}}
    presets = bset.parse_presets(styles)
    group = _block('<!-- wp:group -->\n<div class="wp-block-group"></div>\n<!-- /wp:group -->')
    align = next(f for f in bset.settings_fields(group, presets) if f.key == "align")
    assert "Wide" not in align.choices


def test_colour_choices_say_their_contrast() -> None:
    presets = bset.parse_presets(GLOBAL_STYLES)
    fields = {f.key: f for f in bset.settings_fields(_block(), presets)}
    text_rows = fields["textColor"].choices
    assert text_rows[0] == "Theme default"
    assert any(r.startswith("Accent (") and r.endswith(", passes") for r in text_rows)
    assert any(r.startswith("Pale yellow, 1 to 1") and "too faint" in r for r in text_rows)
    bg_rows = fields["backgroundColor"].choices
    assert bg_rows[0] == "None"
    assert any(r.startswith("Contrast (black), text on it 1") for r in bg_rows)
    assert fields["fontSize"].choices == ["Theme default", "Large"]
    assert fields["align"].label.startswith("Text ")
    letters = [f.label[f.label.index("&") + 1].lower() for f in fields.values() if "&" in f.label]
    assert len(letters) == len(set(letters))


def test_no_palette_means_no_colour_choices() -> None:
    keys = [f.key for f in bset.settings_fields(_block(), None)]
    assert "textColor" not in keys
    assert keys == ["align"]


def test_applying_colours_writes_the_comment_and_the_classes() -> None:
    block = _block()
    bset.apply_settings(
        block, {"align": "center", "textColor": "accent", "backgroundColor": "base",
                "fontSize": "large"}
    )  # fmt: skip
    assert serialize([block]) == (
        '<!-- wp:paragraph {"align":"center","textColor":"accent","backgroundColor":"base",'
        '"fontSize":"large"} -->\n'
        '<p class="has-text-align-center has-accent-color has-base-background-color '
        'has-text-color has-background has-large-font-size">Doors open at nine.</p>\n'
        "<!-- /wp:paragraph -->"
    )
    bset.apply_settings(
        block, {"align": None, "textColor": None, "backgroundColor": None, "fontSize": None}
    )
    assert serialize([block]) == PARAGRAPH


def test_unchanged_settings_leave_the_block_byte_for_byte() -> None:
    markup = '<!-- wp:paragraph {"dropCap":false} -->\n<p class="x">Hi</p>\n<!-- /wp:paragraph -->'
    blocks = parse(markup)
    bset.apply_settings(blocks[0], {"dropCap": False})
    assert serialize(blocks) == markup


def test_block_alignment_goes_after_the_block_class() -> None:
    block = _block(
        '<!-- wp:group -->\n<div class="wp-block-group is-style-x"></div>\n<!-- /wp:group -->'
    )
    bset.apply_settings(block, {"align": "wide"})
    assert '<div class="wp-block-group alignwide is-style-x">' in serialize([block])


def test_generic_settings_keep_their_types() -> None:
    block = _block('<!-- wp:latest-posts {"postsToShow":3,"displayPostDate":true} /-->')
    fields = {f.key: f for f in bset.settings_fields(block, None)}
    assert fields["postsToShow"].kind == "text"
    assert fields["displayPostDate"].kind == "check"
    bset.apply_settings(block, {"postsToShow": "5", "displayPostDate": False})
    assert (
        serialize([block]) == '<!-- wp:latest-posts {"postsToShow":5,"displayPostDate":false} /-->'
    )


def test_spacer_height_is_written_in_its_style() -> None:
    markup = '<!-- wp:spacer -->\n<div style="height:100px" aria-hidden="true" class="wp-block-spacer"></div>\n<!-- /wp:spacer -->'
    block = _block(markup)
    bset.apply_settings(block, {"height": "40px"})
    assert '<div style="height:40px" aria-hidden="true"' in serialize([block])


def test_contrast_warning_only_below_aa() -> None:
    presets = bset.parse_presets(GLOBAL_STYLES)
    assert bset.contrast_warning({"textColor": "accent"}, presets) == ""
    warning = bset.contrast_warning({"textColor": "pale"}, presets)
    assert "too faint for text" in warning and "4.5 to 1" in warning
    assert bset.contrast_warning({}, presets) == ""
    assert bset.contrast_warning({"textColor": "pale"}, None) == ""


class _Api:
    def __init__(self, answers):
        self.answers = answers
        self.asked = []

    def get(self, route, **params):
        self.asked.append(route)
        answer = self.answers[route]
        if isinstance(answer, Exception):
            raise answer
        return answer


def test_fetch_presets_reads_the_active_theme() -> None:
    api = _Api({
        "wp/v2/themes": [{"stylesheet": "radio-theme"}],
        "wp/v2/global-styles/themes/radio-theme": GLOBAL_STYLES,
    })  # fmt: skip
    presets = bset.fetch_presets(api)  # type: ignore[arg-type]
    assert presets is not None and presets.colours[2].slug == "accent"


def test_fetch_presets_gives_none_when_the_site_will_not_say() -> None:
    api = _Api({"wp/v2/themes": WordPressApiError("Not allowed.", status=403)})
    assert bset.fetch_presets(api) is None  # type: ignore[arg-type]


# --------------------------------------------------------------------------- #
# Preview Blocks


POST = (
    '<!-- wp:heading -->\n<h2 class="wp-block-heading">Our schedule</h2>\n<!-- /wp:heading -->\n\n'
    '<!-- wp:image {"id":4} -->\n<figure class="wp-block-image"><img src="a.jpg" alt="The studio"/>'
    "</figure>\n<!-- /wp:image -->\n\n"
    '<!-- wp:latest-posts {"postsToShow":2} /-->\n\n'
    '<!-- wp:table -->\n<figure class="wp-block-table"><table><thead><tr><th>Day</th><th>Show'
    "</th></tr></thead><tbody><tr><td>Monday</td><td>Jazz</td></tr></tbody></table></figure>\n"
    "<!-- /wp:table -->\n\n"
    '<!-- wp:acme/form {"id":3} /-->'
)


def test_preview_renders_dynamic_blocks_and_reads_the_rest() -> None:
    seen = []

    def render(block):
        seen.append((block.name, dict(block.attrs)))
        if block.name == "acme/form":
            raise WordPressApiError("The form plugin is switched off.", status=500)
        return '<ul class="wp-block-latest-posts"><li><a href="/x">Spring fair</a></li></ul>'

    result = bp.render_preview(POST, render)
    assert seen == [("core/latest-posts", {"postsToShow": 2}), ("acme/form", {"id": 3})]
    assert result.rendered == 1
    assert result.failed == ["Form block (from a plugin): The form plugin is switched off."]
    assert result.readout.splitlines() == [
        "Heading level 2: Our schedule",
        "Picture: The studio",
        "- Spring fair",
        "Day | Show",
        "Monday | Jazz",
        "[Form block (from a plugin): the site could not show this.]",
    ]


def test_preview_does_not_change_the_parsed_document() -> None:
    blocks_before = serialize(parse(POST))
    bp.render_preview(POST, lambda _b: "<p>x</p>")
    assert serialize(parse(POST)) == blocks_before


def test_readout_names_what_a_listener_needs() -> None:
    html = (
        "<p>One <em>two</em></p><hr/><img src=x><blockquote><p>Said.</p></blockquote>"
        "<details><summary>More</summary><p>Hidden</p></details><script>no()</script>"
        "<figure><img src=y alt='Cat'><figcaption>A cat</figcaption></figure>"
    )
    assert bp.html_readout(html).splitlines() == [
        "One two",
        "Separator",
        "Picture with no alt text",
        "Quote:",
        "Said.",
        "Details: More",
        "Hidden",
        "Picture: Cat",
        "Caption: A cat",
    ]
