"""Analytics: table-first, honest metrics (PRD 33).

Pure, wx-free computation over the local data the app already holds: the user's
own posts, received items, publication plans, and campaigns. ``compute_metrics``
returns a ``MetricsReport`` whose ``tables()`` yields accessible data tables
first (PRD 33.2) -- headers plus rows -- for posts sent, replies received,
engagement by account and network, posting frequency, schedule reliability,
accessibility completion, and hashtag performance.

``to_csv`` and ``to_markdown`` export any table, and ``compare_periods`` states
plain-language deltas between two reports. Following the PRD's ethics rules (PRD
33.3): only measured data is computed here -- no inferred traits, no covert
tracking -- and interpretation (the deltas) is kept separate from measurement.
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field

from quill_social.model import Campaign, PublicationPlan, SocialItem

_MS_PER_DAY = 86_400_000
_HASHTAG_RE = re.compile(r"#(\w+)")


@dataclass
class Table:
    """One accessible data table (PRD 33.2)."""

    title: str
    headers: list[str]
    rows: list[list] = field(default_factory=list)


@dataclass
class MetricsReport:
    """Measured metrics only; interpretation lives in ``compare_periods`` (PRD 33.3)."""

    posts_sent: int = 0
    replies_received: int = 0
    posts_by_account: dict[str, int] = field(default_factory=dict)
    engagement_by_account: dict[str, int] = field(default_factory=dict)
    posts_by_network: dict[str, int] = field(default_factory=dict)
    engagement_by_network: dict[str, int] = field(default_factory=dict)
    active_days: int = 0
    posting_frequency: float = 0.0
    schedule_published: int = 0
    schedule_failed: int = 0
    schedule_reliability: float = 0.0
    media_posts: int = 0
    media_posts_with_alt: int = 0
    accessibility_completion: float = 0.0
    hashtag_posts: dict[str, int] = field(default_factory=dict)
    hashtag_engagement: dict[str, int] = field(default_factory=dict)

    def tables(self) -> list[Table]:
        overview = Table(
            title="Overview",
            headers=["Metric", "Value"],
            rows=[
                ["Posts sent", self.posts_sent],
                ["Replies received", self.replies_received],
                ["Active days", self.active_days],
                ["Posts per day", round(self.posting_frequency, 2)],
                ["Schedule reliability", round(self.schedule_reliability, 2)],
                ["Accessibility completion", round(self.accessibility_completion, 2)],
            ],
        )
        by_account = Table(
            title="Engagement by account",
            headers=["Account", "Posts", "Engagement"],
            rows=[
                [acct, self.posts_by_account.get(acct, 0), self.engagement_by_account[acct]]
                for acct in sorted(self.engagement_by_account)
            ],
        )
        by_network = Table(
            title="Engagement by network",
            headers=["Network", "Posts", "Engagement"],
            rows=[
                [net, self.posts_by_network.get(net, 0), self.engagement_by_network[net]]
                for net in sorted(self.engagement_by_network)
            ],
        )
        schedule = Table(
            title="Schedule reliability",
            headers=["State", "Count"],
            rows=[
                ["Published", self.schedule_published],
                ["Failed", self.schedule_failed],
            ],
        )
        accessibility = Table(
            title="Accessibility completion",
            headers=["Metric", "Value"],
            rows=[
                ["Media posts", self.media_posts],
                ["Media posts with full alt text", self.media_posts_with_alt],
                ["Completion ratio", round(self.accessibility_completion, 2)],
            ],
        )
        hashtags = Table(
            title="Hashtag performance",
            headers=["Hashtag", "Posts", "Engagement"],
            rows=[
                [tag, self.hashtag_posts.get(tag, 0), self.hashtag_engagement[tag]]
                for tag in sorted(
                    self.hashtag_engagement,
                    key=lambda t: (-self.hashtag_engagement[t], t),
                )
            ],
        )
        return [overview, by_account, by_network, schedule, accessibility, hashtags]


def _engagement(item: SocialItem) -> int:
    return item.reply_count + item.reblog_count + item.favourite_count


def compute_metrics(
    own_posts: list[SocialItem],
    received: list[SocialItem],
    plans: list[PublicationPlan] | None = None,
    campaigns: list[Campaign] | None = None,
) -> MetricsReport:
    """Compute measured metrics from local data (PRD 33.1).

    ``campaigns`` is accepted for symmetry and future campaign-scoped rollups; it
    does not alter the measured totals here.
    """
    plans = plans or []
    report = MetricsReport(posts_sent=len(own_posts))
    report.replies_received = sum(1 for it in received if it.is_reply)

    day_buckets: set[int] = set()
    for it in own_posts:
        eng = _engagement(it)
        report.posts_by_account[it.account_id] = (
            report.posts_by_account.get(it.account_id, 0) + 1
        )
        report.engagement_by_account[it.account_id] = (
            report.engagement_by_account.get(it.account_id, 0) + eng
        )
        report.posts_by_network[it.network] = report.posts_by_network.get(it.network, 0) + 1
        report.engagement_by_network[it.network] = (
            report.engagement_by_network.get(it.network, 0) + eng
        )
        day_buckets.add(it.created_at // _MS_PER_DAY)
        if it.media:
            report.media_posts += 1
            if it.missing_alt_count == 0:
                report.media_posts_with_alt += 1
        for tag in _HASHTAG_RE.findall(it.text):
            tag = tag.lower()
            report.hashtag_posts[tag] = report.hashtag_posts.get(tag, 0) + 1
            report.hashtag_engagement[tag] = report.hashtag_engagement.get(tag, 0) + eng

    report.active_days = len(day_buckets)
    report.posting_frequency = report.posts_sent / max(1, report.active_days)

    for plan in plans:
        if plan.state == "published":
            report.schedule_published += 1
        elif plan.state == "failed":
            report.schedule_failed += 1
    settled = report.schedule_published + report.schedule_failed
    report.schedule_reliability = report.schedule_published / settled if settled else 0.0

    report.accessibility_completion = (
        report.media_posts_with_alt / report.media_posts if report.media_posts else 0.0
    )
    return report


def to_csv(table: Table) -> str:
    """Serialize a table to CSV text (PRD 33.2)."""
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(table.headers)
    for row in table.rows:
        writer.writerow(row)
    return buf.getvalue()


def to_markdown(table: Table) -> str:
    """Serialize a table to a GitHub-flavored Markdown table (PRD 33.2)."""
    lines = [
        "| " + " | ".join(str(h) for h in table.headers) + " |",
        "| " + " | ".join("---" for _ in table.headers) + " |",
    ]
    for row in table.rows:
        lines.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join(lines)


def _delta_line(label: str, a_val: float, b_val: float, *, ratio: bool = False) -> str:
    diff = b_val - a_val
    if ratio:
        a_str, b_str, d_str = f"{a_val:.2f}", f"{b_val:.2f}", f"{diff:+.2f}"
    else:
        a_str, b_str = str(a_val), str(b_val)
        d_str = f"{diff:+d}" if isinstance(diff, int) else f"{diff:+.2f}"
    if diff > 0:
        direction = "up"
    elif diff < 0:
        direction = "down"
    else:
        direction = "unchanged"
    return f"{label}: {a_str} -> {b_str} ({d_str}, {direction})"


def compare_periods(a: MetricsReport, b: MetricsReport) -> list[str]:
    """Plain-language deltas between two reports (PRD 33.2, interpretation layer)."""
    return [
        _delta_line("Posts sent", a.posts_sent, b.posts_sent),
        _delta_line("Replies received", a.replies_received, b.replies_received),
        _delta_line("Posts per day", a.posting_frequency, b.posting_frequency, ratio=True),
        _delta_line(
            "Schedule reliability", a.schedule_reliability, b.schedule_reliability, ratio=True
        ),
        _delta_line(
            "Accessibility completion",
            a.accessibility_completion,
            b.accessibility_completion,
            ratio=True,
        ),
    ]
