"""Find Stations reaching the libraries, not just the station directories.

Quill Radio 3.0 grew fifteen browse branches and Find Stations kept searching the
same eight radio directories. You could walk to a LibriVox book by author and
could not find it by typing its title. This closes that.

Deliberately **not** a new window. The rows land in the results list already on
screen, each carrying its own ``source`` -- "LibriVox", "Internet Archive",
"Project Gutenberg", "Podcasts (Apple)" -- which the Source column already shows
and the Source dropdown already filters by. A second search surface would be a
second thing to learn for no gain, and the merge that de-duplicates across
directories works on these rows unchanged.

Three rules, and the third is the one that is easy to get wrong:

* **Every source is its own task.** One slow library never holds up the others,
  and never holds up the station results, which have already arrived by the time
  this starts.
* **One announcement, at the end.** Not per source and not per arrival: a list
  that announces itself five times is a list nobody can read. The counter is what
  makes "at the end" knowable.
* **A source that cannot be searched is reported once, in words.** "No results
  from Mixcloud" and "Mixcloud cannot be searched" are different facts, only one
  of which means try again with different words -- so the distinction is kept
  even though, as of 2026-08-14, every source in the list *can* be searched.
  Audius, Mixcloud and ccMixter were listed as unsearchable until somebody
  checked; the machinery stays because the next source added may genuinely lack
  a search, and having somewhere honest to put that is what stopped this from
  being discovered sooner.
"""

from __future__ import annotations

from typing import Any

from quill.core.radio import federated_search


def begin(host: Any, query: str) -> None:
    """Search every library for *query*, appending results as each answers."""
    wanted = query.strip()
    if not wanted or host._task_manager is None:
        return
    if host._safe_mode:
        # Every library here is a network source. Said once, rather than five
        # empty branches worth of silence.
        host._announce("The libraries are disabled in Safe Mode; stations only.")
        return

    sources = federated_search.searchable_ids()
    host._library_pending = len(sources)
    host._library_found = 0
    host._library_failed = []
    for source_id in sources:
        _submit(host, source_id, wanted)


def _submit(host: Any, source_id: str, query: str) -> None:
    library = federated_search.source(source_id)
    if library is None:
        return

    def _work(**_kwargs: Any) -> list:
        return federated_search.search_source(source_id, query, safe_mode=host._safe_mode)

    def _ok(_op: str, rows: object) -> None:
        _arrived(host, library, list(rows) if isinstance(rows, list) else [], None)

    def _failed(_op: str, error: BaseException) -> None:
        _arrived(host, library, [], error)

    host._task_manager.submit(
        f"radio-library-{source_id}", _work, on_success=_ok, on_failure=_failed
    )


def _arrived(host: Any, library: Any, rows: list, error: BaseException | None) -> None:
    """One library answered. Merge its rows in, and speak when the last lands."""
    from quill.core.radio.directory_search import merge_and_rank

    host._library_pending = max(0, int(getattr(host, "_library_pending", 1)) - 1)
    if error is not None:
        host._library_failed.append(library.label)
    elif rows:
        host._library_found = int(getattr(host, "_library_found", 0)) + len(rows)
        host._search_extras = list(host._search_extras) + rows
        host._search_results = merge_and_rank(
            [host._search_rb, host._search_extras], host._search_query
        )
        host._show_category_for_library_results()
    if host._library_pending == 0:
        host._announce(summary(host))


def summary(host: Any) -> str:
    """What to say once every library has reported.

    Names any source that cannot be searched at all, because a listener who
    knows a library is in the tree and sees no rows from it should be told which
    of the two possible reasons applies. Currently none are, which is why the
    sentence usually does not appear.
    """
    found = int(getattr(host, "_library_found", 0))
    said = f"{found} more from the libraries." if found else "Nothing in the libraries matched."
    failed = list(getattr(host, "_library_failed", ()))
    if failed:
        said += f" {', '.join(failed)} could not be reached."
    unsearchable = [s.label for s in federated_search.LIBRARY_SOURCES if s.search is None]
    if unsearchable:
        said += f" {', '.join(unsearchable)} can be browsed but not searched."
    return said
