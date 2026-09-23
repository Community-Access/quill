"""The public page: what it says, and what it must never say.

Most of these are about the second half. The page is reachable by anybody with
the address, including somebody who would like the service switched off for
everyone else, so the test that matters most is the one asserting a number is
*absent*.
"""

from __future__ import annotations

import pytest

from tests.conftest import make_user_and_device, seed_config_rows, seed_default_model


def _spend(app, user, device, count=3, cost=0.00004):
    from app.limits import record_usage

    with app.app_context():
        for _ in range(count):
            record_usage(app, user, device, "summarize", "gpt-6-luna", 1200, 300, cost, "allowed")


@pytest.fixture
def busy(app, client, db):
    seed_default_model(db.session)
    seed_config_rows(db.session)
    user, device = make_user_and_device(db.session, token="t")
    _spend(app, user, device, count=5)
    return client


# --- What it must never publish -------------------------------------------------


def test_the_page_never_says_how_much_budget_is_left(busy, app, db):
    """The one that matters.

    Publishing headroom -- "92% of this month's budget used" -- tells anybody who
    would like the service switched off for everybody else exactly how hard to
    push and when. Spending to date is the honest half and carries none of that.
    """
    import re

    # Visible words only, so markup like <caption> cannot look like "cap".
    visible = re.sub(r"<[^>]+>", " ", busy.get("/").get_data(as_text=True)).lower()
    for leak in ("budget", "remaining", "headroom", "% of", "percent of"):
        assert not re.search(rf"{re.escape(leak)}", visible), f"the public page mentions {leak!r}"
    # And no percentage at all: there is no honest one to publish here, so any
    # that appeared would be a fraction of something operational.
    assert "%" not in visible


def test_the_page_never_names_a_person(busy, db):
    """There is nothing to name -- the schema holds no email, no name and no
    document text -- and this asserts the page did not invent a way."""
    from app.models import User

    html = busy.get("/").get_data(as_text=True)
    user = db.session.query(User).first()
    assert user.id not in html
    assert user.support_id not in html


def test_the_page_does_not_publish_the_per_person_allowance_numbers(busy):
    """Saying there *is* an allowance is useful. Publishing the exact caps tells
    somebody sizing an abuse attempt what to size it to."""
    html = busy.get("/").get_data(as_text=True)
    assert "allowance" in html.lower()
    assert "100 requests" not in html
    assert "20 a day" not in html


# --- What it does say -------------------------------------------------------------


def test_the_page_answers_what_happens_to_your_writing(busy):
    """The question somebody actually arrives with."""
    html = busy.get("/").get_data(as_text=True)
    assert "OpenAI" in html
    assert "What is kept" in html
    assert "What is not kept" in html
    assert "what you wrote" in html.lower()


def test_the_page_publishes_what_the_service_has_cost(busy):
    html = busy.get("/").get_data(as_text=True)
    assert "Spent this month" in html
    assert "Spent altogether" in html
    assert "Cost of one answer" in html


def test_the_cost_of_one_answer_is_the_persuasive_number(app, busy, db):
    """A fraction of a penny is the whole reason this can be free, and it is
    more convincing shown than asserted."""
    from app.public_stats import gather

    with app.app_context():
        stats = gather(app)
    assert 0 < stats.cost_per_request_cents < 1


def test_word_counts_are_rounded_rather_than_exact(app, busy, db):
    """Publishing a figure to the digit invites somebody to watch it move and
    infer what one account is doing."""
    from app.public_stats import gather

    with app.app_context():
        words = gather(app).words_read
    assert words % 100 == 0


# --- The states it has to handle ---------------------------------------------------


def test_a_brand_new_deployment_does_not_show_four_zeroes(app, client, db):
    """Which reads as a broken page. It says it is getting started instead,
    which is friendlier and also true."""
    seed_default_model(db.session)
    html = client.get("/").get_data(as_text=True)
    assert "just getting started" in html
    assert "Cost of one answer" not in html


def test_a_paused_service_says_so_at_the_top(app, client, db):
    """Somebody whose AI stopped working will come here to find out why, and
    the answer should be the first thing they hear."""
    from app.models import FeatureFlag

    seed_default_model(db.session)
    db.session.add(
        FeatureFlag(
            feature="hosted_ai",
            enabled=False,
            disabled_reason="We are looking into unusual activity.",
        )
    )
    db.session.commit()

    html = client.get("/").get_data(as_text=True)
    assert "paused right now" in html
    assert "We are looking into unusual activity." in html
    # Unmissable by position rather than by a live region -- see
    # test_the_page_does_not_announce_its_own_arrival.
    assert html.index("paused right now") < html.index("What it does")
    # And it says what still works, so it is not a dead end.
    assert "own API key" in html


# --- The page itself ----------------------------------------------------------------


def test_the_page_needs_no_authentication(client, db):
    assert client.get("/").status_code == 200


def test_the_page_uses_no_javascript(busy):
    html = busy.get("/").get_data(as_text=True)
    assert "<script" not in html.lower()
    assert "onclick" not in html.lower()


def test_the_page_has_the_structure_a_screen_reader_navigates_by(busy):
    html = busy.get("/").get_data(as_text=True)
    assert 'class="skip-link"' in html
    assert "<main" in html
    assert html.count("<h2") >= 5  # headings to jump between
    assert "<caption>" in html
    assert 'lang="en"' in html


def test_the_page_does_not_bury_itself_in_landmarks(busy):
    """Regression. This shipped with seven named <section>s.

    A <section> with an accessible name is a *region* landmark, so that was nine
    landmarks on a page holding one article's worth of prose -- and somebody
    rotoring through them has to walk past all nine to find anything. The
    headings already give that navigation and give it better, because a heading
    list says what each part is about.

    Two landmarks is the whole budget here: where the content is, and the footer.
    """
    html = busy.get("/").get_data(as_text=True)
    assert "aria-labelledby" not in html
    assert "aria-label" not in html
    assert html.count("<main") == 1
    assert html.count("<footer") == 1
    assert html.count("<nav") == 0


def test_the_page_does_not_announce_its_own_arrival(app, client, db):
    """A live region announces a *change*. The paused banner is the state of the
    service when somebody arrived, reached by reading -- firing a live region for
    it competes with the screen reader's own announcement of the page, which is
    the same over-announcing GATE-13 catches on the desktop side."""
    from app.models import FeatureFlag

    seed_default_model(db.session)
    db.session.add(FeatureFlag(feature="hosted_ai", enabled=False, disabled_reason="Maintenance."))
    db.session.commit()

    html = client.get("/").get_data(as_text=True)
    assert 'role="alert"' not in html
    assert 'role="status"' not in html
    # Still unmissable, by position and by wording rather than by a live region.
    assert html.index("paused right now") < html.index("What it does")


def test_the_paused_state_is_not_conveyed_by_colour_alone(app, client, db):
    """WCAG 1.4.1. The banner is styled red; the sentence has to carry it."""
    from app.models import FeatureFlag

    seed_default_model(db.session)
    db.session.add(FeatureFlag(feature="hosted_ai", enabled=False, disabled_reason="Maintenance."))
    db.session.commit()

    html = client.get("/").get_data(as_text=True)
    assert "<strong>The free AI is paused right now.</strong>" in html


def test_every_link_says_where_it_goes(busy):
    """WCAG 2.4.4. No "click here", no bare URLs read out character by
    character."""
    import re

    html = busy.get("/").get_data(as_text=True)
    for text in re.findall(r"<a [^>]*>(.*?)</a>", html, re.S):
        words = re.sub(r"<[^>]+>", " ", text).strip()
        assert words, "a link with no text in it"
        assert words.lower() not in {"here", "click here", "read more", "more", "link"}


def test_the_heading_order_never_skips_a_level(busy):
    """WCAG 1.3.1. A jump from h1 to h3 tells a listener a level exists that
    does not."""
    import re

    html = busy.get("/").get_data(as_text=True)
    levels = [int(m) for m in re.findall(r"<h([1-6])[ >]", html)]
    assert levels[0] == 1
    for previous, current in zip(levels, levels[1:], strict=False):
        assert current <= previous + 1


def test_the_page_carries_its_own_title_and_language(busy):
    """WCAG 2.4.2 and 3.1.1 -- the two a screen reader uses before anything
    else on the page is read at all."""
    html = busy.get("/").get_data(as_text=True)
    assert "<title>QUILL AI" in html
    assert '<html lang="en">' in html


def test_the_figures_are_cached_so_the_page_cannot_hammer_the_database(app, busy, db):
    """A page anybody can load must not be a way to make the service work."""
    from app.public_stats import _CACHE_KEY

    with app.app_context():
        busy.get("/")
        assert app.extensions["gateway_redis"].get(_CACHE_KEY) is not None


def test_an_admin_change_can_drop_the_cache(app, busy, db):
    from app.public_stats import _CACHE_KEY, invalidate

    with app.app_context():
        busy.get("/")
        invalidate(app)
        assert app.extensions["gateway_redis"].get(_CACHE_KEY) is None


def test_a_tiny_spend_is_said_in_words_not_as_zero(app, busy, db):
    """Two decimal places turn the first weeks of this service into a column of
    "$0.00", which next to "0.003 of a cent per answer" reads as a broken page
    rather than a genuinely tiny number."""
    from app.public_stats import PublicStats

    stats = PublicStats()
    assert stats.money(0) == "nothing yet"
    assert stats.money(0.00005) == "less than a cent"
    assert stats.money(4.2) == "$4.20"

    html = busy.get("/").get_data(as_text=True)
    assert "$0.00" not in html
