"""The catalog is opened on one thread and read from another.

That is not a hypothetical: ``catalog_ui`` opens the store on a task-manager
worker during the startup refresh, and every browse afterwards reads it from
the UI thread. sqlite3 refuses a connection used from a thread other than the
one that created it, so a single shared connection raised
``ProgrammingError: SQLite objects created in a thread can only be used in
that same thread`` on **every** catalog-served branch -- and because
``browse()`` swallows a source's errors, the tree fell through to the network
and the whole offline catalog behaved as though it were not there.

Found by reading the installed app's log, not by a test, which is why one
exists now.
"""

from __future__ import annotations

import threading
from pathlib import Path

from quill.core.radio.catalog.refresh import SourceSpec, refresh
from quill.core.radio.catalog.store import CatalogStore, StationRow


def _row(key: str) -> StationRow:
    return StationRow(
        key=key,
        name=f"Station {key}",
        stream_url=f"https://example.org/{key}",
        country="France",
        source_id="radio_browser",
        source_record_id=key,
    )


def _fill(tmp_path: Path) -> CatalogStore:
    store = CatalogStore(tmp_path)
    refresh(
        [SourceSpec("radio_browser", "RB", lambda: iter([[_row("a"), _row("b")]]))],
        store,
        now=1000.0,
    )
    return store


def test_a_store_opened_on_one_thread_reads_from_another(tmp_path: Path) -> None:
    store = _fill(tmp_path)
    # Open on a worker, exactly as the startup refresh does.
    opened: list[int] = []
    worker = threading.Thread(target=lambda: opened.append(len(store.top_voted())))
    worker.start()
    worker.join()
    assert opened == [2]

    # ...then read from this thread, exactly as browsing does.
    assert len(store.top_voted()) == 2
    assert [r.key for r in store.search("station")] == ["a", "b"]
    store.close()


def test_many_threads_can_read_at_once(tmp_path: Path) -> None:
    store = _fill(tmp_path)
    results: list[int] = []
    lock = threading.Lock()

    def read() -> None:
        count = len(store.by_country("France"))
        with lock:
            results.append(count)

    threads = [threading.Thread(target=read) for _ in range(6)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert results == [2] * 6
    store.close()


def test_closing_on_one_thread_leaves_another_thread_working(tmp_path: Path) -> None:
    """close() can only close the calling thread's connection -- and must not
    break a reader that is mid-session on its own."""
    store = _fill(tmp_path)
    worker_ok: list[bool] = []

    def worker() -> None:
        store.top_voted()  # opens this thread's connection
        store.close()  # closes only this one
        worker_ok.append(True)

    thread = threading.Thread(target=worker)
    thread.start()
    thread.join()
    assert worker_ok == [True]
    assert len(store.top_voted()) == 2  # this thread is unaffected
    store.close()
