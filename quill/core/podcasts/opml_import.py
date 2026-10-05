"""Bulk OPML import: planning, deduplication, and reachability checking.

``opml.py`` parses OPML and adds shows one at a time. That is fine for the
thirty-line file somebody exported from another app last week, and it falls
over on the real thing: a two-thousand-entry subscription list accumulated
over a decade, in which a third of the feeds have moved, died, or are listed
twice.

Two problems, both addressed here.

**It was quadratic.** ``PodcastLibrary.add_show`` scans every existing show
to reject a duplicate feed URL, and ``find_or_create_folder_path`` scans
every folder for every path segment of every entry. Importing 2,000 entries
into a library of 2,000 shows meant millions of string comparisons and a
frozen window. :func:`plan_import` builds one index up front and answers
every question in constant time, so the whole plan is O(entries + library).

**It never told you what was wrong.** There was no reachability check at all,
so a dead feed imported silently and stayed in the library forever, and the
import report dialog had no producer. :func:`validate_feeds` probes feeds
concurrently on a bounded pool, reports progress, and can be cancelled
mid-run -- and :func:`prune_opml` writes back the same OPML file minus the
feeds that failed, which is the point of knowing.

Duplicate detection normalizes before comparing. ``http://`` and ``https://``
forms of the same feed are the same feed -- podcasts moved to HTTPS en masse
and old OPML files are full of both -- as are trailing-slash and
case-differing-host variants. What is deliberately *not* merged is two
different feeds that happen to share a title: two shows genuinely can be
called "The Daily", so those are imported and flagged for review rather than
silently dropped.

wx-free, strict-typed. The probe is a reviewed egress site (GATE-9).
"""

from __future__ import annotations

import ssl
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path

from quill.core import http_client
from quill.core.counted import plural
from quill.core.net_retry import retry_transient
from quill.core.podcasts import feed_auth, feed_problems
from quill.core.podcasts.models import PodcastSettings, PodcastShow
from quill.core.podcasts.opml import (
    ImportedShow,
    OpmlValidationResult,
    parse_opml,
    parse_opml_folders,
)
from quill.core.podcasts.subscriptions import PodcastLibrary, new_id

#: Short by design. A probe answers "is anything there", and a feed that
#: takes longer than this to say hello is one worth flagging anyway.
PROBE_TIMEOUT_SECONDS = 8.0
#: Concurrency for the reachability sweep. Enough that 2,000 feeds finish in
#: minutes rather than hours; low enough to stay a well-behaved client and to
#: not saturate a home connection while something is playing.
DEFAULT_WORKERS = 8
#: Only ever read this much of a probe response -- we want the status line,
#: not the feed.
_PROBE_READ_BYTES = 2048
#: Shorter than :data:`quill.core.net_retry.DEFAULT_BACKOFF` on purpose. One
#: feed refresh can afford three seconds of waiting; a sweep of two thousand
#: feeds cannot afford it per feed, so the sweep buys the same protection
#: against a false "dead" verdict at a third of the cost.
_PROBE_BACKOFF: tuple[float, ...] = (0.5, 1.0)
#: Said for an entry whose address is not http or https at all.
_NOT_WEB = "not a web address; it must start with http or https"


def normalize_feed_url(url: str) -> str:
    """A feed URL reduced to what makes two URLs *the same feed*.

    Scheme is discarded entirely (http and https forms of one feed are one
    feed), host is lowercased with any default port dropped, the path loses a
    single trailing slash, and the fragment goes. Query is kept: plenty of
    private feeds carry their token there, and two URLs differing only by
    token are genuinely two different subscriptions.
    """
    text = (url or "").strip()
    if not text:
        return ""
    try:
        parsed = urllib.parse.urlsplit(text)
    except ValueError:
        return text.casefold()
    host = (parsed.hostname or "").casefold()
    port = parsed.port
    if port and not (
        (parsed.scheme == "http" and port == 80) or (parsed.scheme == "https" and port == 443)
    ):
        host = f"{host}:{port}"
    path = parsed.path.rstrip("/")
    query = f"?{parsed.query}" if parsed.query else ""
    return f"{host}{path}{query}"


@dataclass(slots=True)
class ImportCandidate:
    """One OPML entry that survived planning and is ready to add."""

    title: str
    feed_url: str
    homepage: str
    folder_path: list[str]
    #: What the file said about the show, carried through to the new
    #: subscription (check.md bug 15). Downcast's export has none of these;
    #: plenty of other apps' exports do, and the older one-at-a-time import
    #: already kept them -- so the Import OPML window was the one that lost them.
    description: str = ""
    language: str = ""
    category: str = ""


def _host_problem(feed_url: str) -> str:
    """Why *feed_url* is not a complete web address, or ``""``.

    One real Downcast export carried ``http://feed/`` for Braillecast: a
    scheme and a word, which imported fine and then failed every check for
    ever with "getaddrinfo failed" (check.md bug 12). A podcast host has a dot
    in its name (or is an IP address); ``localhost`` is allowed for somebody
    testing their own feed.
    """
    try:
        host = urllib.parse.urlsplit(feed_url).hostname or ""
    except ValueError:
        return "not a complete web address"
    if not host:
        return "not a complete web address"
    if host == "localhost" or "." in host or ":" in host:
        return ""
    return "not a complete web address"


@dataclass(slots=True)
class ImportPlan:
    """What a bulk import will do, decided before anything is changed.

    Every list holds display strings ready for the report, except
    :attr:`new`, which holds the records to add. Deciding first and acting
    second is what makes the import reportable, cancellable, and testable
    without a library to mutate.
    """

    new: list[ImportCandidate] = field(default_factory=list)
    #: Already subscribed (matched on the normalized URL).
    duplicates_in_library: list[str] = field(default_factory=list)
    #: Listed more than once inside the OPML file itself.
    duplicates_in_file: list[str] = field(default_factory=list)
    #: Imported, but a show with this title is already subscribed under a
    #: different feed. Flagged, never dropped -- two shows can share a name.
    same_title_different_feed: list[str] = field(default_factory=list)
    #: Entries that could not be used at all, with the reason.
    unusable: list[tuple[str, str]] = field(default_factory=list)
    #: Every folder the file has, as name paths in document order -- empty
    #: ones included, so the file's structure arrives whole.
    folders: list[list[str]] = field(default_factory=list)

    @property
    def total_seen(self) -> int:
        return (
            len(self.new)
            + len(self.duplicates_in_library)
            + len(self.duplicates_in_file)
            + len(self.unusable)
        )

    def summary(self) -> str:
        return (
            f"{plural(self.total_seen, 'entry', 'entries')} read: {len(self.new)} new, "
            f"{len(self.duplicates_in_library)} already followed, "
            f"{len(self.duplicates_in_file)} listed twice in the file, "
            f"{len(self.unusable)} unusable."
        )


def _where(path: list[str]) -> str:
    return " / ".join(path) if path else "the top level"


def plan_import(
    library: PodcastLibrary,
    entries: Iterable[ImportedShow],
    *,
    folders: Iterable[list[str]] = (),
) -> ImportPlan:
    """Decide what to import, in one pass over *entries*.

    Indexes the library once (two dicts), so each entry costs a couple of
    hash lookups regardless of how large either side is. Nothing is mutated.
    *folders* is the file's own folder list (:func:`parse_opml_folders`).
    """
    plan = ImportPlan(folders=[list(path) for path in folders])
    subscribed: dict[str, str] = {}
    titles: dict[str, str] = {}
    for show in library.shows:
        if show.feed_url:
            subscribed[normalize_feed_url(show.feed_url)] = show.title
        if show.title:
            titles.setdefault(show.title.casefold(), show.feed_url)
    seen_in_file: dict[str, list[str]] = {}
    #: Titles already met *in this file*, with the entry that first used it --
    #: one Downcast export had eleven pairs of different feeds sharing a name
    #: (Dateline NBC twice, The Mayan Crystal on two hosts), and in six of them
    #: one copy was dead. Only the library was compared before (check.md bug 11).
    titles_in_file: dict[str, tuple[str, str]] = {}
    flagged: set[str] = set()

    def flag(label: str) -> None:
        if label not in flagged:
            flagged.add(label)
            plan.same_title_different_feed.append(label)

    for entry in entries:
        feed_url = (entry.feed_url or "").strip()
        title = (entry.title or "").strip() or feed_url
        if not feed_url:
            plan.unusable.append((title or "(untitled)", "no feed URL"))
            continue
        if not feed_url.lower().startswith(("http://", "https://")):
            plan.unusable.append((f"{title} ({feed_url})", _NOT_WEB))
            continue
        bad_host = _host_problem(feed_url)
        if bad_host:
            plan.unusable.append((f"{title} ({feed_url})", bad_host))
            continue
        key = normalize_feed_url(feed_url)
        if key in subscribed:
            plan.duplicates_in_library.append(f"{title} ({feed_url})")
            continue
        if key in seen_in_file:
            # One podcast filed in two folders: it is followed once, in the
            # first place the file lists it, and the report says both places.
            first = seen_in_file[key]
            entry_path = list(entry.folder_path)
            if entry_path != first:
                plan.duplicates_in_file.append(
                    f"{title} ({feed_url}), also listed in {_where(entry_path)}; "
                    f"kept in {_where(first)}"
                )
            else:
                plan.duplicates_in_file.append(f"{title} ({feed_url})")
            continue
        seen_in_file[key] = list(entry.folder_path)
        label = f"{title} ({feed_url})"
        existing_feed = titles.get(title.casefold())
        if existing_feed and normalize_feed_url(existing_feed) != key:
            flag(label)
        earlier = titles_in_file.get(title.casefold())
        if earlier is not None and earlier[0] != key:
            flag(earlier[1])
            flag(label)
        titles_in_file.setdefault(title.casefold(), (key, label))
        plan.new.append(
            ImportCandidate(
                title=title,
                feed_url=feed_url,
                homepage=(entry.homepage or "").strip(),
                folder_path=list(entry.folder_path),
                description=str(getattr(entry, "description", "") or ""),
                language=str(getattr(entry, "language", "") or ""),
                category=str(getattr(entry, "category", "") or ""),
            )
        )
    return plan


def apply_plan(
    library: PodcastLibrary,
    plan: ImportPlan,
    *,
    stream_only: bool = False,
    into_folder: str | None = None,
) -> list[PodcastShow]:
    """Add every planned show to *library*; returns the shows added.

    Folder paths are memoized, so a file whose two thousand entries live in
    forty folders walks the folder tree forty times rather than two thousand.
    ``library.add_show`` is deliberately bypassed: the plan has already ruled
    out duplicates in constant time, and re-scanning every show per entry is
    exactly the quadratic behavior this module exists to remove.
    """
    folder_cache: dict[tuple[str, ...], str | None] = {}
    added: list[PodcastShow] = []

    def resolve_folder(path: list[str]) -> str | None:
        full = tuple([into_folder, *path] if into_folder else path)
        if not full:
            return None
        if full in folder_cache:
            return folder_cache[full]
        folder_id = library.find_or_create_folder_path(list(full))
        folder_cache[full] = folder_id
        return folder_id

    # The file's folders first, in its own order, so empty ones exist and the
    # tree reads in the order the file gave it.
    for path in plan.folders:
        resolve_folder(path)
    for candidate in plan.new:
        show = PodcastShow(
            id=new_id(),
            title=candidate.title,
            feed_url=candidate.feed_url,
            homepage=candidate.homepage,
            folder_id=resolve_folder(candidate.folder_path),
            description=candidate.description,
            language=candidate.language,
            category=candidate.category,
        )
        if stream_only:
            show.settings = PodcastSettings(playback_mode="stream")
        library.shows.append(show)
        added.append(show)
    return added


@dataclass(frozen=True, slots=True)
class OpmlImportOutcome:
    """One completed file import: the plan that was applied, spoken plainly.

    The one-call path below exists for the apps that want an OPML file to
    simply *become subscriptions* -- Quill Radio's Station menu -- without
    assembling parse/plan/apply/save themselves. Cast's richer flow (report
    dialog, reachability sweep, prune-back) keeps calling the pieces.
    """

    added: int
    already_followed: int
    duplicates_in_file: int
    unusable: int

    @property
    def spoken(self) -> str:
        if not self.added and not self.already_followed:
            return "Nothing could be imported from that file."
        parts = [f"Imported {self.added} podcast{'s' if self.added != 1 else ''}"]
        if self.already_followed:
            parts.append(f"{self.already_followed} already followed")
        if self.duplicates_in_file:
            parts.append(f"{self.duplicates_in_file} listed twice in the file")
        if self.unusable:
            parts.append(f"{self.unusable} unusable")
        return ", ".join(parts) + ". Find them under Podcasts, Subscriptions, and in Quill Cast."


def import_opml_file(data_dir: Path | str, opml_path: Path | str) -> OpmlImportOutcome:
    """Parse *opml_path*, add every new show to the shared library, and save.

    Folder outlines in the file become library folders (nested paths
    honored), so an export from an app that organizes by folder arrives
    organized. Deduplication is :func:`plan_import`'s (normalized URLs);
    already-followed shows are counted, never duplicated. Atomic persistence
    via :func:`~quill.core.podcasts.subscriptions.save_library` is what makes
    the import permanent -- both Radio and Cast read this one store.
    """
    from pathlib import Path

    from quill.core.podcasts.subscriptions import load_library, save_library

    text = Path(opml_path).read_text(encoding="utf-8", errors="replace")
    entries = parse_opml(text)
    library = load_library(Path(data_dir))
    plan = plan_import(library, entries, folders=parse_opml_folders(text))
    folders_before = len(library.folders)
    added = apply_plan(library, plan)
    if added or plan.new or len(library.folders) != folders_before:
        save_library(Path(data_dir), library)
    return OpmlImportOutcome(
        added=len(added),
        already_followed=len(plan.duplicates_in_library),
        duplicates_in_file=len(plan.duplicates_in_file),
        unusable=len(plan.unusable),
    )


# -- reachability ------------------------------------------------------------


def probe_feed(url: str, *, timeout: float = PROBE_TIMEOUT_SECONDS) -> OpmlValidationResult:
    """Ask one feed whether it is still there. Never raises.

    A GET rather than a HEAD: too many podcast hosts and CDNs answer HEAD
    with 405 or an outright lie, which would report healthy feeds as broken.
    Only the first couple of kilobytes are read, so the cost is a round trip
    and not a download.

    A 401/403 **with a sign-in challenge** (``WWW-Authenticate``) counts as
    reachable: a private feed demanding a sign-in is alive and worth keeping,
    and pruning it would delete exactly the subscriptions that are hardest to
    get back. Without one it is not a sign-in at all -- a 403 is a host
    refusing podcast apps (a bot check), a 401 a publisher that has locked the
    feed -- and it is reported, in plain words (check.md bug 6).

    The couple of kilobytes read are *looked at* (check.md bug 3): a web page
    where the feed should be is reported, and so is a feed whose whole text
    fits in that sample with no episode in it.

    ``corrected_url`` is set only for a **permanent** move -- 301 or 308 on
    every hop. A temporary redirect is not a new address (check.md bugs 4, 5).

    A transient failure is retried (:mod:`quill.core.net_retry`), and this is
    the call site that most needs it: a "dead feed" verdict here is what the
    import report offers to prune out of the listener's OPML file, so a 503
    from one busy moment must not be what talks somebody into deleting a
    live subscription. The schedule is deliberately shorter than the default
    (:data:`_PROBE_BACKOFF`) -- a sweep runs over thousands of feeds, so the
    worst case is bounded by keeping the waits small rather than by skipping
    the retry that makes the answer trustworthy. A 404 and an address that
    does not resolve are still one round trip each, which is what keeps a
    genuinely dead list fast to sweep.
    """
    from quill.core.podcasts.feed_reader import permanent_landing

    title = url
    if not url.lower().startswith(("http://", "https://")):
        return OpmlValidationResult(title, url, False, _NOT_WEB)
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": http_client.podcast_user_agent(),
            "Accept": "application/rss+xml, application/xml, */*",
        },
    )
    context = ssl.create_default_context()

    def _probe_once() -> OpmlValidationResult:
        """One attempt. The reviewed egress site; the retry wraps it."""
        with feed_auth.recording_redirects() as hops:
            with feed_auth.urlopen_auth_safe(request, timeout=timeout, context=context) as response:
                head: bytes = response.read(_PROBE_READ_BYTES)
        verdict = sniff(head)
        if verdict:
            return OpmlValidationResult(title, url, False, feed_problems.sentence_for(verdict))
        landed = permanent_landing(url, list(hops))
        corrected = (
            landed if landed and normalize_feed_url(landed) != normalize_feed_url(url) else ""
        )
        return OpmlValidationResult(title, url, True, "", corrected)

    try:
        return retry_transient(_probe_once, backoff=_PROBE_BACKOFF)
    except urllib.error.HTTPError as error:
        problem = feed_problems.classify(error)
        if problem.kind == feed_problems.SIGN_IN:
            return OpmlValidationResult(title, url, True, "", "")
        return OpmlValidationResult(title, url, False, problem.sentence)
    except (urllib.error.URLError, TimeoutError, ssl.SSLError, OSError, ValueError) as error:
        return OpmlValidationResult(title, url, False, feed_problems.plain(error))


def sniff(head: bytes) -> str:
    """What the first bytes of a 200 answer say is wrong, or ``""``.

    ``web_page`` when it is HTML rather than a feed. ``empty`` when the whole
    feed fits in the sample and carries no item or entry -- the cheap half of
    "this feed has no episodes"; a bigger empty feed is caught by the first
    check after the import, which reads the whole thing.
    """
    if feed_problems.looks_like_html(head):
        return feed_problems.WEB_PAGE
    text = head.decode("utf-8", errors="replace").lower()
    closed = "</rss>" in text or "</feed>" in text or "</channel>" in text
    if closed and "<item" not in text and "<entry" not in text:
        return feed_problems.EMPTY
    return ""


def validate_feeds(
    feeds: list[tuple[str, str]],
    *,
    workers: int = DEFAULT_WORKERS,
    timeout: float = PROBE_TIMEOUT_SECONDS,
    on_progress: Callable[[int, int], None] | None = None,
    should_cancel: Callable[[], bool] | None = None,
    safe_mode: bool = False,
) -> list[OpmlValidationResult]:
    """Probe every ``(title, feed_url)`` concurrently; returns the results.

    Bounded concurrency, progress after every completion, and a cancel check
    between completions -- a sweep of two thousand feeds is a minutes-long
    operation, and one you cannot stop is one nobody should start. Cancelling
    returns what has finished so far rather than throwing it away.

    Safe Mode does no network at all and reports so per feed, rather than
    pretending every feed is fine.
    """
    total = len(feeds)
    if not total:
        return []
    if safe_mode:
        return [
            OpmlValidationResult(title, url, False, "not checked: Safe Mode blocks the network")
            for title, url in feeds
        ]
    results: list[OpmlValidationResult] = []
    done = 0
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = {
            pool.submit(probe_feed, url, timeout=timeout): (title, url) for title, url in feeds
        }
        for future in as_completed(futures):
            title, url = futures[future]
            try:
                result = future.result()
            except Exception as error:  # noqa: BLE001 - one bad probe never stops the sweep
                result = OpmlValidationResult(title, url, False, feed_problems.plain(error))
            # probe_feed only knows the URL; restore the show's own title so
            # the report reads as a list of shows, not a list of URLs.
            results.append(
                OpmlValidationResult(
                    title, result.feed_url, result.ok, result.error, result.corrected_url
                )
            )
            done += 1
            if on_progress is not None:
                on_progress(done, total)
            if should_cancel is not None and should_cancel():
                for pending in futures:
                    pending.cancel()
                break
    return results


def parse_and_plan(library: PodcastLibrary, text: str) -> ImportPlan:
    """Parse OPML text and plan the import in one call (the worker entry)."""
    return plan_import(library, parse_opml(text), folders=parse_opml_folders(text))


# Re-exported: the import window and its tests reach both through this module.
from quill.core.podcasts.opml_import_after import (  # noqa: E402
    apply_permanent_moves as apply_permanent_moves,
)
from quill.core.podcasts.opml_import_after import (  # noqa: E402
    prune_opml as prune_opml,
)

__all__ = [
    "DEFAULT_WORKERS",
    "PROBE_TIMEOUT_SECONDS",
    "ImportCandidate",
    "ImportPlan",
    "apply_permanent_moves",
    "apply_plan",
    "normalize_feed_url",
    "parse_and_plan",
    "plan_import",
    "probe_feed",
    "prune_opml",
    "sniff",
    "validate_feeds",
]
