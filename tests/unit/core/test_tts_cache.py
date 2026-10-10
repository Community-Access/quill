"""Tests for the synthesized-TTS sentence cache (PERF-3, PERF-10)."""

from __future__ import annotations

import threading
from pathlib import Path

import pytest

from quill.core.tts_cache import (
    TtsCache,
    cached_sentence_generator,
    signature,
)


def _write_wav(path: Path, payload: bytes = b"RIFFfake-wav-data") -> None:
    path.write_bytes(payload)


def test_signature_is_stable_and_distinguishes_inputs() -> None:
    a = signature(("piper", "v1"), "Hello world.")
    b = signature(("piper", "v1"), "Hello world.")
    c = signature(("piper", "v2"), "Hello world.")
    d = signature(("piper", "v1"), "Goodbye world.")
    assert a == b
    assert a != c
    assert a != d


def test_put_then_get_round_trips(tmp_path: Path) -> None:
    cache = TtsCache(tmp_path / "cache")
    source = tmp_path / "src.wav"
    _write_wav(source)
    stored = cache.put("k1", source)
    assert stored.exists()
    hit = cache.get("k1")
    assert hit is not None
    assert hit.read_bytes() == source.read_bytes()


def test_get_missing_returns_none(tmp_path: Path) -> None:
    cache = TtsCache(tmp_path / "cache")
    assert cache.get("nope") is None


def test_lru_evicts_oldest_when_entry_cap_exceeded(tmp_path: Path) -> None:
    cache = TtsCache(tmp_path / "cache", max_entries=2, max_bytes=10**9)
    src = tmp_path / "src.wav"
    _write_wav(src)
    cache.put("a", src)
    cache.put("b", src)
    # Touch "a" so "b" becomes the least-recently-used entry.
    assert cache.get("a") is not None
    cache.put("c", src)
    assert cache.get("a") is not None
    assert cache.get("c") is not None
    assert cache.get("b") is None


def test_byte_budget_bounds_total_size(tmp_path: Path) -> None:
    payload = b"x" * 100
    cache = TtsCache(tmp_path / "cache", max_entries=10**6, max_bytes=250)
    src = tmp_path / "src.wav"
    src.write_bytes(payload)
    cache.put("a", src)
    cache.put("b", src)
    cache.put("c", src)
    # Only two 100-byte entries fit under the 250-byte budget.
    remaining = [k for k in ("a", "b", "c") if cache.get(k) is not None]
    assert len(remaining) == 2
    assert cache.get("c") is not None


def test_existing_files_are_indexed_on_construction(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    _write_wav(cache_dir / "preexisting.wav")
    cache = TtsCache(cache_dir)
    assert cache.get("preexisting") is not None


def test_cached_generator_renders_once_then_reuses(tmp_path: Path) -> None:
    cache = TtsCache(tmp_path / "cache")
    calls: list[str] = []

    def render(sentence: str, out: Path) -> None:
        calls.append(sentence)
        _write_wav(out, payload=b"RIFF" + sentence.encode("utf-8"))

    gen = cached_sentence_generator(("piper", "voiceA"), render, cache=cache)

    out1 = tmp_path / "o1.wav"
    gen("Repeated sentence.", out1)
    assert calls == ["Repeated sentence."]
    assert out1.read_bytes() == b"RIFFRepeated sentence."

    # Second identical render must be served from cache, not re-synthesized.
    out2 = tmp_path / "o2.wav"
    gen("Repeated sentence.", out2)
    assert calls == ["Repeated sentence."]
    assert out2.read_bytes() == out1.read_bytes()

    # A different sentence renders again.
    out3 = tmp_path / "o3.wav"
    gen("A new sentence.", out3)
    assert calls == ["Repeated sentence.", "A new sentence."]


def test_cached_generator_uses_a_hard_link_when_available(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache = TtsCache(tmp_path / "cache")
    calls: list[str] = []

    def render(sentence: str, out: Path) -> None:
        calls.append(sentence)
        _write_wav(out, payload=b"RIFF" + sentence.encode("utf-8"))

    gen = cached_sentence_generator(("piper", "voiceA"), render, cache=cache)
    gen("Repeated sentence.", tmp_path / "first.wav")

    def fail_copy(_source: Path, _destination: Path) -> None:
        raise AssertionError("same-volume cache hit should not copy audio bytes")

    monkeypatch.setattr("quill.core.tts_cache.shutil.copyfile", fail_copy)
    out = tmp_path / "second.wav"
    gen("Repeated sentence.", out)

    assert calls == ["Repeated sentence."]
    assert out.read_bytes() == b"RIFFRepeated sentence."


def test_cached_generator_separates_engine_configs(tmp_path: Path) -> None:
    cache = TtsCache(tmp_path / "cache")
    calls: list[tuple[str, str]] = []

    def make(tag: str) -> object:
        def render(sentence: str, out: Path) -> None:
            calls.append((tag, sentence))
            _write_wav(out, payload=tag.encode("utf-8"))

        return render

    gen_a = cached_sentence_generator(("piper", "voiceA"), make("A"), cache=cache)
    gen_b = cached_sentence_generator(("piper", "voiceB"), make("B"), cache=cache)

    gen_a("Same text.", tmp_path / "a.wav")
    gen_b("Same text.", tmp_path / "b.wav")
    # Same sentence, different voice config -> both must render.
    assert calls == [("A", "Same text."), ("B", "Same text.")]


def test_cache_is_safe_under_concurrent_access(tmp_path: Path) -> None:
    cache = TtsCache(tmp_path / "cache", max_entries=64, max_bytes=10**9)

    def render(sentence: str, out: Path) -> None:
        _write_wav(out, payload=sentence.encode("utf-8"))

    gen = cached_sentence_generator(("piper", "voiceA"), render, cache=cache)
    errors: list[BaseException] = []

    def worker(index: int) -> None:
        try:
            for _ in range(20):
                out = tmp_path / f"w{index}_{threading.get_ident()}.wav"
                gen(f"sentence {index % 8}", out)
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert not errors
