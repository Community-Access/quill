"""Concurrency tests for Quill's lazily-loaded module-level caches (CQ-15).

These exercise the double-checked locking documented in
``docs/QUILL-PRD.md``: when many threads hit a cold cache at
once, the expensive load must run at most once and every thread must observe the
same fully-built, immutable snapshot without raising.
"""

from __future__ import annotations

import threading
from pathlib import Path

import pytest

from quill.core import spellcheck, thesaurus

_THREADS = 16
_CALLS_PER_THREAD = 40


def _hammer(target: object) -> list[BaseException]:
    """Run *target* from many threads at once, collecting any exceptions."""
    errors: list[BaseException] = []
    barrier = threading.Barrier(_THREADS)

    def worker() -> None:
        try:
            barrier.wait()
            for _ in range(_CALLS_PER_THREAD):
                target()
        except BaseException as exc:  # noqa: BLE001 - report, don't swallow
            errors.append(exc)

    workers = [threading.Thread(target=worker) for _ in range(_THREADS)]
    for thread in workers:
        thread.start()
    for thread in workers:
        thread.join(timeout=10.0)
    return errors


@pytest.mark.timeout(90)
def test_thesaurus_index_loads_once_under_concurrent_first_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Same class of flakiness as test_reset_caches.py's thesaurus test: a real
    # cold parse of the 18.5MB th_en_US_v2.dat, this time under a 16-thread
    # thundering herd. Fast in isolation (~2s), but occasionally starved past
    # the global 30s budget under full-suite resource contention.
    # Force a cold cache so every thread races on the first load.
    monkeypatch.setattr(thesaurus, "_INDEX", None, raising=False)
    monkeypatch.setattr(thesaurus, "_LOAD_ERROR", None, raising=False)

    parse_calls = 0
    real_parse = thesaurus._parse_mythes

    def counting_parse(text: str) -> dict[str, list[thesaurus.Meaning]]:
        nonlocal parse_calls
        parse_calls += 1
        return real_parse(text)

    monkeypatch.setattr(thesaurus, "_parse_mythes", counting_parse)

    errors = _hammer(lambda: thesaurus.lookup("happy"))

    assert errors == []
    # The double-checked lock must collapse the race to a single build.
    if thesaurus.is_available():
        assert parse_calls == 1
    else:
        assert parse_calls == 0
    # A definitive result is published exactly once.
    assert thesaurus._INDEX is not None


def test_spellcheck_wordlist_loads_once_under_concurrent_first_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Cold both spell-check caches so threads race on first access.
    monkeypatch.setattr(spellcheck, "_WORDLIST_CACHE", None, raising=False)
    monkeypatch.setattr(spellcheck, "_ENCHANT_DICT", None, raising=False)
    monkeypatch.setattr(spellcheck, "_ENCHANT_TRIED", False, raising=False)

    wordlist_reads = 0
    real_read_text = Path.read_text

    def counting_read_text(self: Path, *args: object, **kwargs: object) -> str:
        nonlocal wordlist_reads
        if self == spellcheck._WORDLIST_PATH:
            wordlist_reads += 1
        return real_read_text(self, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(Path, "read_text", counting_read_text)

    errors = _hammer(lambda: spellcheck.is_known_word("hello"))

    assert errors == []
    # The wordlist file is read at most once even under a thundering herd.
    assert wordlist_reads <= 1


def test_backend_info_is_consistent_across_threads(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(spellcheck, "_WORDLIST_CACHE", None, raising=False)
    monkeypatch.setattr(spellcheck, "_ENCHANT_DICT", None, raising=False)
    monkeypatch.setattr(spellcheck, "_ENCHANT_TRIED", False, raising=False)

    seen_names: set[str] = set()
    lock = threading.Lock()

    def record() -> None:
        name = spellcheck.backend_info().name
        with lock:
            seen_names.add(name)

    errors = _hammer(record)

    assert errors == []
    # Every thread must agree on the single active backend tier.
    assert len(seen_names) == 1
