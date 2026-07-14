from quill.core.format_speech import describe_format_transition, describe_inline_format


def test_plain_text_is_silent() -> None:
    assert describe_inline_format() == ""


def test_bold_only() -> None:
    assert describe_inline_format(bold=True) == "bold"


def test_bold_italic_combined() -> None:
    assert describe_inline_format(bold=True, italic=True) == "bold italic"


def test_link() -> None:
    assert describe_inline_format(href="http://x") == "link"


def test_heading_level() -> None:
    assert describe_inline_format(heading_level=2) == "heading level 2"


def test_heading_with_inline() -> None:
    assert describe_inline_format(heading_level=1, bold=True) == "heading level 1, bold"


def test_bullet_with_inline() -> None:
    assert describe_inline_format(bullet=True, italic=True) == "bullet, italic"


def test_transition_enter_bold() -> None:
    assert describe_format_transition("", "bold") == "bold"


def test_transition_leave_to_plain() -> None:
    assert describe_format_transition("bold", "") == "plain"


def test_transition_no_change_is_silent() -> None:
    assert describe_format_transition("bold", "bold") == ""


def test_underline_spoken() -> None:
    assert describe_inline_format(underline=True) == "underline"


def test_font_and_size_spoken_first() -> None:
    phrase = describe_inline_format(font_family="Arial", font_size_pt=14, bold=True)
    assert phrase == "Arial, 14 point, bold"


def test_alignment_and_color() -> None:
    phrase = describe_inline_format(align="center", color="red")
    assert phrase == "centered, red"


def test_alignment_phrases() -> None:
    assert describe_inline_format(align="left") == "left aligned"
    assert describe_inline_format(align="right") == "right aligned"
    assert describe_inline_format(align="justify") == "justified"


def test_highlight_spoken() -> None:
    assert describe_inline_format(highlight="yellow") == "yellow highlight"


def test_full_run_description_order() -> None:
    phrase = describe_inline_format(
        font_family="Calibri",
        font_size_pt=12,
        bold=True,
        underline=True,
        align="center",
        color="#C00000",
        highlight="yellow",
    )
    assert phrase == "Calibri, 12 point, bold underline, centered, #C00000, yellow highlight"


def test_zero_size_not_spoken() -> None:
    assert describe_inline_format(font_size_pt=0) == ""


def test_strike_super_sub_spoken() -> None:
    assert describe_inline_format(strike=True) == "strikethrough"
    assert describe_inline_format(superscript=True) == "superscript"
    assert describe_inline_format(subscript=True) == "subscript"


def test_line_spacing_phrases() -> None:
    assert describe_inline_format(line_spacing="2") == "double spaced"
    assert describe_inline_format(line_spacing="1.5") == "1.5 line spacing"
    assert describe_inline_format(line_spacing="1") == "single spaced"


def test_named_style_spoken() -> None:
    assert describe_inline_format(named_style="quote") == "quote style"


def test_spacing_and_indent_spoken() -> None:
    phrase = describe_inline_format(space_before=12, indent=36, first_line_indent=18)
    assert phrase == "space before, indented, first line indent"
