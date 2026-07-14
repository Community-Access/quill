"""N-6: ``spellcheck.reset_caches()`` and ``thesaurus.reset_caches()`` reset
their respective module-global caches in a thread-safe way, so the perf
budget tests no longer poke private globals by hand.
"""

from __future__ import annotations

import threading
from pathlib import Path

import pytest

import quill.core.spellcheck as spellcheck
import quill.core.thesaurus as thesaurus


def test_spellcheck_reset_caches_clears_all_globals() -> None:
    # Prime the caches, then ensure reset clears every field.
    spellcheck._WORDLIST_CACHE = frozenset({"alpha", "beta"})
    spellcheck._ENCHANT_DICT = object()
    spellcheck._ENCHANT_TRIED = True
    spellcheck.reset_caches()
    assert spellcheck._WORDLIST_CACHE is None
    assert spellcheck._ENCHANT_DICT is None
    assert spellcheck._ENCHANT_TRIED is False


def test_spellcheck_reset_caches_acquires_backend_lock() -> None:
    # N-6: the helper must take ``_BACKEND_LOCK`` so it cannot race the
    # warm-up / lazy loaders.
    acquired = threading.Event()
    release = threading.Event()

    def _hold() -> None:
        with spellcheck._BACKEND_LOCK:
            acquired.set()
            release.wait(timeout=2)

    holder = threading.Thread(target=_hold, daemon=True)
    holder.start()
    assert acquired.wait(timeout=1)
    spellcheck.reset_caches()
    release.set()
    holder.join(timeout=2)
    assert spellcheck._WORDLIST_CACHE is None


def test_spellcheck_preload_after_reset_loads_wordlist(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # After reset the next preload should reload the bundled wordlist
    # (fallback path) -- sanity check the helper actually drops the cache.
    wordlist = tmp_path / "words_alpha.txt"
    wordlist.write_text("alpha\nbeta\n", encoding="utf-8")
    monkeypatch.setattr(spellcheck, "_WORDLIST_PATH", wordlist)
    spellcheck.reset_caches()
    spellcheck.preload()
    assert "alpha" in spellcheck._load_wordlist()


def test_spellcheck_preload_warms_suggestion_buckets(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # #527: preload must also build the length-bucketed suggestion index so the
    # first F7 spell review does not pay that one-time cost on the UI thread.
    wordlist = tmp_path / "words_alpha.txt"
    wordlist.write_text("alpha\nbeta\ngamma\n", encoding="utf-8")
    monkeypatch.setattr(spellcheck, "_WORDLIST_PATH", wordlist)
    spellcheck.reset_caches()
    assert spellcheck._LENGTH_BUCKETS_BY_WORDLIST_ID == {}  # cold after reset
    spellcheck.preload()
    loaded = spellcheck._load_wordlist()
    assert id(loaded) in spellcheck._LENGTH_BUCKETS_BY_WORDLIST_ID  # warmed by preload


def test_thesaurus_reset_caches_clears_index_and_error() -> None:
    thesaurus._INDEX = {"happy": []}
    thesaurus._LOAD_ERROR = "boom"
    thesaurus.reset_caches()
    assert thesaurus._INDEX is None
    assert thesaurus._LOAD_ERROR is None


def test_thesaurus_reset_caches_acquires_load_lock() -> None:
    # N-6: the helper must take ``_LOAD_LOCK`` to coordinate with
    # ``_ensure_loaded``.
    acquired = threading.Event()
    release = threading.Event()

    def _hold() -> None:
        with thesaurus._LOAD_LOCK:
            acquired.set()
            release.wait(timeout=2)

    holder = threading.Thread(target=_hold, daemon=True)
    holder.start()
    assert acquired.wait(timeout=1)
    thesaurus.reset_caches()
    release.set()
    holder.join(timeout=2)
    assert thesaurus._INDEX is None


@pytest.mark.timeout(90)
def test_thesaurus_preload_after_reset_is_idempotent() -> None:
    # windows-latest CI runners occasionally take much longer than the
    # global 30s budget to read+parse the 18.5MB th_en_US_v2.dat on first
    # touch (Windows Defender scanning a freshly checked-out file), the
    # same flakiness tests/unit/core/test_thesaurus.py is excluded from
    # Windows CI runs for. A longer timeout keeps this test's real
    # reset/preload coverage instead of skipping it outright.
    thesaurus.reset_caches()
    thesaurus.preload()
    thesaurus.preload()
    assert thesaurus._INDEX is not None
