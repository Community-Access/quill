"""A deterministic, credential-free network for the P0 experience (PRD 42).

The mock adapter lets the entire application -- reading, threading, composing,
favouriting, bookmarking, thread splitting, scheduling -- run and be tested
before a single real account is added. Its content is fixed and seeded from a
base timestamp so tests can assert on exact posts, and publishing appends to an
in-memory log and returns a stable id.

Nothing here touches the network. It is the reference implementation of
``NetworkAdapter`` and the thing the accessible shell drives out of the box.
"""

from __future__ import annotations

from quill_social.adapters.base import (
    NetworkAdapter,
    PublishRequest,
    PublishResult,
)
from quill_social.capabilities import Capabilities, default_for
from quill_social.model import Media, Poll, PollOption, SocialItem

_HOUR = 3_600_000
_MIN = 60_000

# A fixed cast so rows are recognizable and tests can assert on them.
_AUTHORS = [
    ("@ada@mock.social", "Ada Lovelace"),
    ("@grace@mock.social", "Grace Hopper"),
    ("@alan@mock.social", "Alan Turing"),
    ("@katherine@mock.social", "Katherine Johnson"),
    ("@bits@mock.social", "BITS Accessibility"),
]


class MockNetwork(NetworkAdapter):
    """An in-memory network seeded with a deterministic timeline."""

    name = "mock"

    def __init__(self, account_id: str = "acct_mock", *, base_ms: int = 1_700_000_000_000):
        self.account_id = account_id
        self.base_ms = base_ms
        self._published: list[SocialItem] = []
        self._seq = 0
        self._home = self._seed_home()

    # -- capabilities ---------------------------------------------------------

    def capabilities(self) -> Capabilities:
        return default_for("mock")

    # -- reading --------------------------------------------------------------

    def home_timeline(self, *, limit: int = 40, since_id: str = "") -> list[SocialItem]:
        items = list(self._published[::-1]) + self._home
        if since_id:
            out = []
            for it in items:
                if it.remote_id == since_id:
                    break
                out.append(it)
            items = out
        return items[:limit]

    def notifications(self, *, limit: int = 40) -> list[SocialItem]:
        # The subset of home that mentions the user, plus one reply notification.
        notes = [it for it in self._home if "@you" in it.text][:limit]
        return notes

    def thread(self, item: SocialItem) -> list[SocialItem]:
        root_remote = item.thread_root or item.remote_id
        chain = [it for it in self._home if (it.thread_root == root_remote
                                             or it.remote_id == root_remote)]
        chain.sort(key=lambda it: it.created_at)
        return chain

    # -- writing --------------------------------------------------------------

    def publish(self, request: PublishRequest) -> PublishResult:
        self._seq += 1
        remote_id = f"mock-{self._seq:05d}"
        item = SocialItem(
            network="mock",
            account_id=self.account_id,
            remote_id=remote_id,
            uri=f"mock://post/{remote_id}",
            author_handle="@you@mock.social",
            author_display="You",
            text=request.text,
            visibility=request.visibility,
            content_warning=request.content_warning,
            lang=request.lang,
            in_reply_to=request.in_reply_to,
            created_at=self.base_ms + self._seq * _MIN,
            media=list(request.media),
        )
        self._published.append(item)
        return PublishResult(remote_id=remote_id, uri=item.uri, item=item)

    def set_favourite(self, remote_id: str, on: bool = True) -> None:
        self._flag(remote_id, "favourited", on)

    def set_bookmark(self, remote_id: str, on: bool = True) -> None:
        self._flag(remote_id, "bookmarked", on)

    def set_reblog(self, remote_id: str, on: bool = True) -> None:
        self._flag(remote_id, "reblogged", on)

    def _flag(self, remote_id: str, attr: str, on: bool) -> None:
        for it in self._home:
            if it.remote_id == remote_id:
                setattr(it, attr, on)

    # -- seed data ------------------------------------------------------------

    def _mk(self, n: int, author_idx: int, text: str, **kw) -> SocialItem:
        handle, display = _AUTHORS[author_idx % len(_AUTHORS)]
        return SocialItem(
            network="mock",
            account_id=self.account_id,
            remote_id=f"seed-{n:03d}",
            uri=f"mock://post/seed-{n:03d}",
            author_handle=handle,
            author_display=display,
            author_id=handle,
            text=text,
            created_at=self.base_ms - n * 7 * _MIN,
            **kw,
        )

    def _seed_home(self) -> list[SocialItem]:
        items: list[SocialItem] = []

        items.append(self._mk(
            1, 0,
            "Just shipped an accessibility fix for the timeline. Focus no longer "
            "jumps to the top on refresh. @you should try it.",
            reply_count=4, reblog_count=9, favourite_count=22,
        ))

        items.append(self._mk(
            2, 4,
            "New guide: keyboard-first social reading. Every action has a shortcut "
            "and every state is spoken.",
            media=[Media(kind="image", uri="mock://img/guide.png",
                         alt_text="Cover reading 'Keyboard-First Social'.")],
            reply_count=2, reblog_count=15, favourite_count=40, bookmarked=True,
        ))

        items.append(self._mk(
            3, 1,
            "Reminder: describe your images. A photo with no alt text is a locked "
            "door.",
            media=[Media(kind="image", uri="mock://img/nodesc.png")],  # missing alt
            reply_count=1, reblog_count=30, favourite_count=51,
        ))

        cw = self._mk(
            4, 2,
            "Long thread about election-night data crunching ahead.",
            content_warning="Politics", sensitive=True,
            reply_count=6, reblog_count=3, favourite_count=8,
        )
        items.append(cw)

        # A short thread rooted at seed-005.
        root = self._mk(
            5, 3,
            "1/ Let's talk about how we calculated orbital trajectories by hand.",
            reply_count=2, reblog_count=12, favourite_count=61,
        )
        root.thread_root = "seed-005"
        # A real thread is chronological: the root is oldest, replies follow.
        root.created_at = self.base_ms - 20 * _MIN
        items.append(root)
        r1 = self._mk(
            6, 3,
            "2/ We checked the machine's math. Trust, but verify.",
            reply_count=1, reblog_count=4, favourite_count=33,
        )
        r1.in_reply_to = "seed-005"
        r1.thread_root = "seed-005"
        r1.thread_level = 1
        r1.created_at = self.base_ms - 19 * _MIN
        items.append(r1)
        r2 = self._mk(
            7, 3,
            "3/ The point: accuracy is an accessibility feature too.",
            reblog_count=6, favourite_count=45,
        )
        r2.in_reply_to = "seed-006"
        r2.thread_root = "seed-005"
        r2.thread_level = 2
        r2.created_at = self.base_ms - 18 * _MIN
        items.append(r2)

        poll = self._mk(
            8, 0,
            "Which pane order do you prefer for the reader?",
            reply_count=3, reblog_count=1, favourite_count=5,
        )
        poll.poll = Poll(
            options=[
                PollOption("Navigation, list, details", 42),
                PollOption("List, navigation, details", 17),
                PollOption("One pane at a time", 63),
            ],
            multiple=False,
            total_votes=122,
        )
        items.append(poll)

        boost = self._mk(
            9, 1,
            "Boosting: the new field reader lets you hear exactly the columns you "
            "want, in the order you want.",
            reblog_of="seed-002", reblog_by="@grace@mock.social",
            reblog_count=15, favourite_count=40,
        )
        items.append(boost)

        for i in range(10, 16):
            items.append(self._mk(
                i, i,
                f"Cached post number {i}. This is here so search, paging, and "
                f"catch-up have real volume to work with.",
                reply_count=i % 3, reblog_count=i % 4, favourite_count=i,
            ))

        return items
