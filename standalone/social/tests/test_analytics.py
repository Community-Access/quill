"""Tests for analytics metrics and exports (PRD 33)."""

from quill_social.model import Media, PublicationPlan, SocialItem
from quill_social.services import analytics as an


def _post(account="acct1", network="mock", text="hello", created=0, **kw):
    return SocialItem(
        account_id=account,
        network=network,
        text=text,
        created_at=created,
        **kw,
    )


def test_posts_sent_and_replies_received():
    own = [_post(), _post()]
    received = [
        _post(in_reply_to="x"),  # a reply
        _post(),  # not a reply
    ]
    report = an.compute_metrics(own, received)
    assert report.posts_sent == 2
    assert report.replies_received == 1


def test_engagement_by_account_and_network():
    own = [
        _post(account="a", network="mock", reply_count=1, favourite_count=2),
        _post(account="b", network="bluesky", reblog_count=3),
    ]
    report = an.compute_metrics(own, [])
    assert report.engagement_by_account["a"] == 3
    assert report.engagement_by_account["b"] == 3
    assert report.engagement_by_network["mock"] == 3
    assert report.posts_by_account["a"] == 1


def test_accessibility_completion_ratio():
    own = [
        _post(media=[Media(alt_text="described")]),
        _post(media=[Media(alt_text="")]),  # missing alt
        _post(),  # no media, ignored
    ]
    report = an.compute_metrics(own, [])
    assert report.media_posts == 2
    assert report.media_posts_with_alt == 1
    assert report.accessibility_completion == 0.5


def test_schedule_reliability():
    plans = [
        PublicationPlan(state="published"),
        PublicationPlan(state="published"),
        PublicationPlan(state="failed"),
        PublicationPlan(state="queued"),  # not settled
    ]
    report = an.compute_metrics([], [], plans)
    assert report.schedule_published == 2
    assert report.schedule_failed == 1
    assert report.schedule_reliability == 2 / 3


def test_posting_frequency_uses_active_days():
    own = [
        _post(created=0),
        _post(created=1000),  # same day
        _post(created=an._MS_PER_DAY + 5),  # next day
    ]
    report = an.compute_metrics(own, [])
    assert report.active_days == 2
    assert report.posting_frequency == 1.5


def test_hashtag_performance():
    own = [_post(text="love #Python", favourite_count=5)]
    report = an.compute_metrics(own, [])
    assert report.hashtag_posts["python"] == 1
    assert report.hashtag_engagement["python"] == 5


def test_tables_shape():
    report = an.compute_metrics([_post()], [])
    tables = report.tables()
    titles = [t.title for t in tables]
    assert "Overview" in titles
    assert "Schedule reliability" in titles
    for t in tables:
        for row in t.rows:
            assert len(row) == len(t.headers)


def test_to_csv_shape():
    table = an.Table(title="T", headers=["A", "B"], rows=[[1, 2], [3, 4]])
    csv_text = an.to_csv(table)
    lines = csv_text.strip().split("\n")
    assert lines[0] == "A,B"
    assert lines[1] == "1,2"
    assert len(lines) == 3


def test_to_markdown_shape():
    table = an.Table(title="T", headers=["A", "B"], rows=[[1, 2]])
    md = an.to_markdown(table)
    lines = md.split("\n")
    assert lines[0] == "| A | B |"
    assert lines[1] == "| --- | --- |"
    assert lines[2] == "| 1 | 2 |"


def test_compare_periods_deltas():
    a = an.compute_metrics([_post()], [])
    b = an.compute_metrics([_post(), _post()], [])
    deltas = an.compare_periods(a, b)
    assert any("Posts sent: 1 -> 2 (+1, up)" == d for d in deltas)
    assert len(deltas) == 5
