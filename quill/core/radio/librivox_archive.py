"""LibriVox books by way of the Internet Archive.

**This is not a second LibriVox branch.** It is the same branch, served by
whichever route is up.

LibriVox and the Internet Archive looked like duplicated sources and are not:
LibriVox *is* hosted on the Archive. librivox.org supplies the catalogue
(genres, authors, section listings) while every recording it points at lives in
the Archive's ``librivoxaudio`` collection. So the two branches were never
showing the same thing twice -- they were showing a catalogue and a warehouse.

That distinction became load-bearing on 2026-08-16, when librivox.org went
behind a Cloudflare 522 (its origin timing out) for hours and the LibriVox
branch was simply dead, while the identical books answered fine from the
Archive. A branch with one route is only as reliable as its worst day; this
module is the second route, used when the first cannot answer.

What is lost by coming this way is real and worth stating: the Archive knows an
item's subject and creator, not LibriVox's curated genre list or its
section-by-section reader credits. So the fallback returns *books*, opened as
Archive items, and says so in the note rather than pretending to be the
catalogue.
"""

from __future__ import annotations

from quill.core.radio import internet_archive

#: The Archive collection every LibriVox recording is filed in.
COLLECTION = "collection:librivoxaudio"

#: Newest first, which is what "Recently Added" means.
RECENT_SORT = "addeddate desc"

#: Said on every row that came this way, so nobody has to guess why the
#: reader credits are missing.
VIA_ARCHIVE_NOTE = "from the Internet Archive"


def _quoted(value: str) -> str:
    """A Lucene phrase, with the quoting that would break it removed.

    A genre or author name is user-reachable text; an unescaped quote would end
    the phrase early and the rest would be parsed as query syntax.
    """
    return '"' + value.replace("\\", " ").replace('"', " ").strip() + '"'


def recent(*, limit: int = 40, safe_mode: bool = False) -> list:
    """The most recently added LibriVox recordings."""
    return internet_archive.search(COLLECTION, limit=limit, sort=RECENT_SORT, safe_mode=safe_mode)


def by_genre(genre: str, *, limit: int = 40, safe_mode: bool = False) -> list:
    """LibriVox recordings the Archive files under *genre*.

    The Archive's ``subject`` is close to, but not the same as, LibriVox's
    genre. Close enough to browse; not close enough to claim it is the same
    list, which is why the caller labels these rows.
    """
    wanted = genre.strip()
    if not wanted:
        return []
    return internet_archive.search(
        f"{COLLECTION} AND subject:{_quoted(wanted)}", limit=limit, safe_mode=safe_mode
    )


def by_author(author: str, *, limit: int = 40, safe_mode: bool = False) -> list:
    """LibriVox recordings the Archive credits to *author*."""
    wanted = author.strip()
    if not wanted:
        return []
    return internet_archive.search(
        f"{COLLECTION} AND creator:{_quoted(wanted)}", limit=limit, safe_mode=safe_mode
    )
