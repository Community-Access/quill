"""Pictures inside a WordPress document: which, their words, their size (wordpress.md 6.5, 6.8)."""

from __future__ import annotations

from quill.core.ai.doc_images import list_document_images
from quill.core.wordpress import media_alt as ma

HTML = (
    "<h2>Spring fair</h2>\n"
    "<p>Our volunteers ran the stall all day.</p>\n"
    '<figure class="wp-block-image"><a href="https://radio.example/fair">'
    '<img src="https://radio.example/u/fair-1024x683.jpg" alt="" class="wp-image-5" '
    'width="1024" height="683"/></a><figcaption>Photo: Sam</figcaption></figure>\n'
    "<p>Thanks to everyone who came.</p>\n"
)

MD = (
    "# Schedule\n\nThe morning show starts at seven.\n\n"
    '![IMG_2041.jpg](https://radio.example/u/studio.jpg "The studio") {id=12}\n\n'
    "Call in any time.\n"
)


def test_image_at_the_caret_or_on_its_line() -> None:
    inside = HTML.index("wp-image-5")
    assert ma.image_at(HTML, inside).source.endswith("fair-1024x683.jpg")
    line_start = MD.index("![")
    assert ma.image_at(MD, line_start + 2) is not None
    assert ma.image_at(MD, MD.index("{id=12}") + 3) is not None  # same line, after the markup
    assert ma.image_at(MD, 2) is None


def test_media_id_from_class_marker_and_block() -> None:
    assert ma.media_id_in(HTML, list_document_images(HTML)[0]) == 5
    assert ma.media_id_in(MD, list_document_images(MD)[0]) == 12
    block = '<!-- wp:image {"id":31} --><figure><img src="a.jpg" alt="x"/></figure>'
    assert ma.media_id_in(block, list_document_images(block)[0]) == 31
    closed = '<!-- wp:image {"id":31} --><!-- /wp:image --><img src="b.jpg" alt="y"/>'
    assert ma.media_id_in(closed, list_document_images(closed)[0]) == 0


def test_with_source_swaps_address_and_width() -> None:
    image = list_document_images(HTML)[0]
    revised = ma.with_source(HTML, image, "https://radio.example/u/fair-300x200.jpg", 300)
    assert 'src="https://radio.example/u/fair-300x200.jpg"' in revised
    assert 'width="300"' in revised and "height=" not in revised
    plain = '<img src="a.jpg" alt="x"/>'
    assert 'width="640"' in ma.with_source(plain, list_document_images(plain)[0], "b.jpg", 640)
    md_image = list_document_images(MD)[0]
    assert "(https://radio.example/u/studio-300.jpg" in ma.with_source(
        MD, md_image, "https://radio.example/u/studio-300.jpg", 300
    )
    unwidth = ma.with_source(HTML, image, "https://radio.example/u/fair.jpg", 0)
    assert "width=" not in unwidth


def test_alt_problems() -> None:
    assert ma.alt_problem("", "a.jpg") == "no alternative text"
    assert ma.alt_problem("IMG_2041.jpg", "studio.jpg") == "looks like a file name"
    assert ma.alt_problem("DSC 0042", "x.jpg") == "looks like a file name"
    assert ma.alt_problem("studio.jpg", "https://x/studio.jpg") == "looks like a file name"
    assert ma.alt_problem("x" * 200, "a.jpg") == "long, 200 characters"
    assert ma.alt_problem("Image of a cat", "a.jpg") == "starts with 'image of'"
    assert ma.alt_problem("Two presenters at the microphones", "a.jpg") == ""


def test_review_rows_and_decorative() -> None:
    rows = ma.review_rows(MD + '\n<img src="d.png" alt="" role="presentation"/>\n')
    assert rows[0].spoken() == "1. studio.jpg: looks like a file name: IMG_2041.jpg"
    assert rows[1].decorative and rows[1].spoken() == "2. d.png: decorative"
    fine = ma.review_rows('<img src="a.jpg" alt="Two presenters"/>')
    assert fine[0].spoken() == "1. a.jpg: Two presenters"


def test_mark_decorative_then_set_alt_takes_it_off() -> None:
    text = '<p>x</p><img src="a.jpg" alt="old"/>'
    image = list_document_images(text)[0]
    marked = ma.mark_decorative(text, image)
    assert 'role="presentation"' in marked and 'alt=""' in marked
    again = list_document_images(marked)[0]
    assert ma.mark_decorative(marked, again) == marked
    restored = ma.set_alt(marked, again, "A red door")
    assert 'alt="A red door"' in restored and "role=" not in restored
    md = "![old](a.jpg)"
    assert ma.mark_decorative(md, list_document_images(md)[0]) == "![](a.jpg)"


def test_context_gives_heading_neighbours_caption_and_link() -> None:
    context = ma.image_context(HTML, list_document_images(HTML)[0])
    assert context.heading == "Spring fair"
    assert context.before == "Our volunteers ran the stall all day."
    assert context.after == "Thanks to everyone who came."
    assert context.caption == "Photo: Sam"
    assert context.link == "https://radio.example/fair"
    md = ma.image_context(MD, list_document_images(MD)[0])
    assert md.heading == "Schedule"
    assert md.caption == "The studio"
    assert md.after == "Call in any time."


def test_the_question_carries_the_rules_and_the_context() -> None:
    question = ma.alt_text_question(ma.image_context(HTML, list_document_images(HTML)[0]))
    assert "image of" in question and "a person" in question and "DECORATIVE" in question
    assert "The heading above it: Spring fair" in question
    assert "It is a link to https://radio.example/fair" in question
    assert "heading above" not in ma.alt_text_question(ma.ImageContext())


def test_clean_suggestion() -> None:
    assert ma.clean_suggestion('"Image of two presenters at the desk."').alt == (
        "Two presenters at the desk."
    )
    assert ma.clean_suggestion("Alt text: a red door").alt == "A red door"
    assert ma.clean_suggestion("DECORATIVE").decorative
    chart = ma.clean_suggestion("Listeners by year.\nFULLER DESCRIPTION: 2024 had 400.")
    assert chart.alt == "Listeners by year." and chart.fuller == "2024 had 400."
