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
import xml.etree.ElementTree as ET
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path

from quill import __version__
from quill.core.net_retry import retry_transient
from quill.core.podcasts.models import PodcastSettings, PodcastShow
from quill.core.podcasts.opml import (
    ImportedShow,
    OpmlValidationResult,
    parse_opml,
)
from quill.core.podcasts.subscriptions import PodcastLibrary, new_id
from quill.core.safe_xml import ParseError, UnsafeXMLError
from quill.core.safe_xml import fromstring as safe_fromstring

_USER_AGENT = f"QUILL/{__version__} (https://github.com/Community-Access/quill)"
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
            f"{self.total_seen} entr(ies) read: {len(self.new)} new, "
            f"{len(self.duplicates_in_library)} already subscribed, "
            f"{len(self.duplicates_in_file)} listed twice in the file, "
            f"{len(self.unusable)} unusable."
        )


def plan_import(library: PodcastLibrary, entries: Iterable[ImportedShow]) -> ImportPlan:
    """Decide what to import, in one pass over *entries*.

    Indexes the library once (two dicts), so each entry costs a couple of
    hash lookups regardless of how large either side is. Nothing is mutated.
    """
    plan = ImportPlan()
    subscribed: dict[str, str] = {}
    titles: dict[str, str] = {}
    for show in library.shows:
        if show.feed_url:
            subscribed[normalize_feed_url(show.feed_url)] = show.title
        if show.title:
            titles.setdefault(show.title.casefold(), show.feed_url)
    seen_in_file: dict[str, str] = {}
    for entry in entries:
        feed_url = (entry.feed_url or "").strip()
        title = (entry.title or "").strip() or feed_url
        if not feed_url:
            plan.unusable.append((title or "(untitled)", "no feed URL"))
            continue
        if not feed_url.lower().startswith(("http://", "https://")):
            plan.unusable.append((f"{title} ({feed_url})", "not an http(s) URL"))
            continue
        key = normalize_feed_url(feed_url)
        if key in subscribed:
            plan.duplicates_in_library.append(f"{title} ({feed_url})")
            continue
        if key in seen_in_file:
            plan.duplicates_in_file.append(f"{title} ({feed_url})")
            continue
        seen_in_file[key] = title
        existing_feed = titles.get(title.casefold())
        if existing_feed and normalize_feed_url(existing_feed) != key:
            plan.same_title_different_feed.append(f"{title} ({feed_url})")
        plan.new.append(
            ImportCandidate(
                title=title,
                feed_url=feed_url,
                homepage=(entry.homepage or "").strip(),
                folder_path=list(entry.folder_path),
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

    for candidate in plan.new:
        show = PodcastShow(
            id=new_id(),
            title=candidate.title,
            feed_url=candidate.feed_url,
            homepage=candidate.homepage,
            folder_id=resolve_folder(candidate.folder_path),
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
    plan = plan_import(library, entries)
    added = apply_plan(library, plan)
    if added or plan.new:
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

    A 401/403 counts as **reachable**: a private feed demanding a sign-in is
    alive and worth keeping, and pruning it would delete exactly the
    subscriptions that are hardest to get back.

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
    title = url
    if not url.lower().startswith(("http://", "https://")):
        return OpmlValidationResult(title, url, False, "not an http(s) URL")
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": _USER_AGENT,
            "Accept": "application/rss+xml, application/xml, */*",
        },
    )
    context = ssl.create_default_context()

    def _probe_once() -> OpmlValidationResult:
        """One attempt. The reviewed egress site; the retry wraps it."""
        with urllib.request.urlopen(  # noqa: S310 - scheme checked above
            request, timeout=timeout, context=context
        ) as response:
            response.read(_PROBE_READ_BYTES)
            final_url = str(getattr(response, "url", "") or url)
            corrected = (
                final_url
                if final_url and normalize_feed_url(final_url) != normalize_feed_url(url)
                else ""
            )
            return OpmlValidationResult(title, url, True, "", corrected)

    try:
        return retry_transient(_probe_once, backoff=_PROBE_BACKOFF)
    except urllib.error.HTTPError as error:
        if error.code in (401, 403):
            return OpmlValidationResult(title, url, True, "", "")
        return OpmlValidationResult(title, url, False, f"HTTP {error.code} {error.reason}")
    except (urllib.error.URLError, TimeoutError, ssl.SSLError, OSError, ValueError) as error:
        return OpmlValidationResult(title, url, False, str(error) or "could not connect")


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
                result = OpmlValidationResult(title, url, False, str(error))
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


# -- pruning -----------------------------------------------------------------


def prune_opml(text: str, dead_urls: Iterable[str]) -> str:
    """The same OPML with every unreachable feed's outline removed.

    Structure, attributes, folder nesting, and anything the original file
    carried that QUILL does not model are all preserved -- this edits the
    document rather than re-exporting the library, so the pruned file is
    still recognisably the listener's own file and can go straight back to
    wherever it came from. A folder outline left with no feeds in it is
    dropped too, since an empty folder is not a subscription list.
    """
    dead = {normalize_feed_url(url) for url in dead_urls if url}
    if not dead:
        return text
    try:
        root = safe_fromstring(text)
    except (ParseError, UnsafeXMLError):
        return text

    def prune_element(element: ET.Element) -> None:
        for child in list(element.findall("outline")):
            xml_url = (child.get("xmlUrl") or "").strip()
            if xml_url:
                if normalize_feed_url(xml_url) in dead:
                    element.remove(child)
                continue
            prune_element(child)
            if not child.findall("outline"):
                element.remove(child)

    body = root.find("body")
    if body is not None:
        prune_element(body)
    return ET.tostring(root, encoding="unicode", xml_declaration=False)


def parse_and_plan(library: PodcastLibrary, text: str) -> ImportPlan:
    """Parse OPML text and plan the import in one call (the worker entry)."""
    return plan_import(library, parse_opml(text))


__all__ = [
    "DEFAULT_WORKERS",
    "PROBE_TIMEOUT_SECONDS",
    "ImportCandidate",
    "ImportPlan",
    "apply_plan",
    "normalize_feed_url",
    "parse_and_plan",
    "plan_import",
    "probe_feed",
    "prune_opml",
    "validate_feeds",
]
