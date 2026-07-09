"""Tests for the pluggable lexical service layer (DICT-1)."""

from __future__ import annotations

import pytest

import quill.core.lexical as lexical
from quill.core.lexical import (
    SOURCE_BOTH,
    SOURCE_OFFLINE,
    SOURCE_ONLINE,
    DatamuseProvider,
    Definition,
    EncyclopediaEntry,
    FreeDictionaryProvider,
    LexicalProvider,
    LexicalResult,
    LexicalService,
    LookupItem,
    MergedTerm,
    OfflineLexicalProvider,
    WikipediaProvider,
    build_lookup_items,
    merge_terms,
    merged_terms_for_mode,
    normalize_datamuse,
    normalize_free_dictionary,
    normalize_source_mode,
    normalize_wikipedia,
    render_lookup,
)


class _StubOffline(LexicalProvider):
    name = "offline"
    online = False

    def __init__(self, result: LexicalResult | None) -> None:
        self._result = result

    def lookup(self, word: str) -> LexicalResult | None:
        return self._result


class _StubOnline(LexicalProvider):
    name = "stub-online"
    online = True

    def __init__(self, result: LexicalResult | None, *, calls: list[str] | None = None) -> None:
        self._result = result
        self._calls = calls if calls is not None else []

    def lookup(self, word: str) -> LexicalResult | None:
        self._calls.append(word)
        return self._result


def test_normalize_free_dictionary_extracts_definitions_and_synonyms() -> None:
    payload = {
        "word": "happy",
        "entries": [
            {
                "partOfSpeech": "adjective",
                "senses": [
                    {
                        "definition": "feeling pleasure",
                        "examples": ["a happy child"],
                        "synonyms": ["glad", "joyful"],
                        "antonyms": ["sad"],
                    }
                ],
            }
        ],
    }
    result = normalize_free_dictionary("happy", payload)
    assert result is not None
    assert result.definitions[0] == Definition("adjective", "feeling pleasure", "a happy child")
    assert "glad" in result.synonyms
    assert "sad" in result.antonyms
    assert result.sources == ("Free Dictionary",)


def test_normalize_free_dictionary_returns_none_for_empty() -> None:
    assert normalize_free_dictionary("x", {"entries": []}) is None
    assert normalize_free_dictionary("x", None) is None
    assert normalize_free_dictionary("x", "garbage") is None


def test_normalize_datamuse_dedupes_and_orders() -> None:
    payload = [
        {"word": "glad", "score": 100},
        {"word": "Glad", "score": 90},
        {"word": "joyful", "score": 80},
        {"not_word": 1},
    ]
    assert normalize_datamuse(payload) == ("glad", "joyful")
    assert normalize_datamuse("nope") == ()


def test_service_offline_only_never_calls_online() -> None:
    calls: list[str] = []
    offline = _StubOffline(LexicalResult(word="cat", synonyms=("feline",), sources=("offline",)))
    online = _StubOnline(LexicalResult(word="cat", synonyms=("kitty",)), calls=calls)
    service = LexicalService(offline=offline, online=[online])

    result = service.lookup("cat", online=False)

    assert result.synonyms == ("feline",)
    assert calls == []  # consent off: no online provider was queried


def test_service_merges_online_when_enabled() -> None:
    offline = _StubOffline(LexicalResult(word="cat", synonyms=("feline",), sources=("offline",)))
    online = _StubOnline(
        LexicalResult(
            word="cat",
            definitions=(Definition("noun", "a small animal"),),
            synonyms=("kitty",),
            sources=("Datamuse",),
        )
    )
    service = LexicalService(offline=offline, online=[online])

    result = service.lookup("cat", online=True)

    assert "feline" in result.synonyms
    assert "kitty" in result.synonyms
    assert result.definitions[0].text == "a small animal"
    assert "offline" in result.sources
    assert "Datamuse" in result.sources


def test_service_falls_back_to_offline_when_online_raises() -> None:
    class _Boom(LexicalProvider):
        name = "boom"
        online = True

        def lookup(self, word: str) -> LexicalResult | None:
            raise RuntimeError("network down")

    offline = _StubOffline(LexicalResult(word="cat", synonyms=("feline",), sources=("offline",)))
    service = LexicalService(offline=offline, online=[_Boom()])

    result = service.lookup("cat", online=True)

    assert result.synonyms == ("feline",)


def test_service_caches_results() -> None:
    calls: list[str] = []
    offline = _StubOffline(LexicalResult(word="cat", synonyms=("feline",)))
    online = _StubOnline(LexicalResult(word="cat", synonyms=("kitty",)), calls=calls)
    service = LexicalService(offline=offline, online=[online])

    service.lookup("cat", online=True)
    service.lookup("cat", online=True)

    assert calls == ["cat"]  # second call served from cache


def test_service_blank_word_returns_empty() -> None:
    service = LexicalService(offline=_StubOffline(None), online=[])
    result = service.lookup("   ", online=True)
    assert result.is_empty
    assert result.word == ""


def test_offline_provider_uses_thesaurus(monkeypatch: pytest.MonkeyPatch) -> None:
    from quill.core import thesaurus

    class _Entry:
        word = "happy"
        all_synonyms = ("glad", "joyful")

    monkeypatch.setattr(thesaurus, "lookup", lambda word: _Entry())
    result = OfflineLexicalProvider().lookup("happy")
    assert result is not None
    assert result.synonyms == ("glad", "joyful")
    assert result.sources == ("offline",)


def test_free_dictionary_provider_uses_http(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, str] = {}

    def fake_get(url: str, *, timeout: float = 8.0) -> object:
        captured["url"] = url
        return {"entries": [{"partOfSpeech": "noun", "senses": [{"definition": "a test"}]}]}

    monkeypatch.setattr(lexical, "_http_get_json", fake_get)
    result = FreeDictionaryProvider().lookup("exam")
    assert result is not None
    assert "freedictionaryapi.com/api/v1/entries/en/exam" in captured["url"]
    assert result.definitions[0].text == "a test"


def test_datamuse_provider_queries_all_relations(monkeypatch: pytest.MonkeyPatch) -> None:
    urls: list[str] = []

    def fake_get(url: str, *, timeout: float = 8.0) -> object:
        urls.append(url)
        if "rel_syn" in url:
            return [{"word": "glad"}]
        return []

    monkeypatch.setattr(lexical, "_http_get_json", fake_get)
    result = DatamuseProvider().lookup("happy")
    assert result is not None
    assert result.synonyms == ("glad",)
    assert any("rel_syn" in u for u in urls)
    assert any("rel_ant" in u for u in urls)
    assert any("rel_rhy" in u for u in urls)
    assert any("ml=" in u for u in urls)


def test_normalize_wikipedia_extracts_title_summary_and_url() -> None:
    payload = {
        "title": "Ada Lovelace",
        "extract": "Ada Lovelace was an English mathematician.",
        "content_urls": {"desktop": {"page": "https://en.wikipedia.org/wiki/Ada_Lovelace"}},
    }
    result = normalize_wikipedia("Ada Lovelace", payload)
    assert result is not None
    assert result.encyclopedia == (
        EncyclopediaEntry(
            title="Ada Lovelace",
            summary="Ada Lovelace was an English mathematician.",
            url="https://en.wikipedia.org/wiki/Ada_Lovelace",
        ),
    )
    assert result.sources == ("Wikipedia",)


def test_normalize_wikipedia_returns_none_for_disambiguation() -> None:
    payload = {"title": "Mercury", "extract": "Mercury may refer to:", "type": "disambiguation"}
    assert normalize_wikipedia("Mercury", payload) is None


def test_normalize_wikipedia_returns_none_for_missing_extract() -> None:
    assert normalize_wikipedia("x", {"title": "X"}) is None
    assert normalize_wikipedia("x", None) is None
    assert normalize_wikipedia("x", "not a dict") is None


def test_wikipedia_provider_uses_rest_summary_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, str] = {}

    def fake_get(url: str, *, timeout: float = 8.0) -> object:
        captured["url"] = url
        return {"title": "Test", "extract": "A test summary."}

    monkeypatch.setattr(lexical, "_http_get_json", fake_get)
    result = WikipediaProvider().lookup("Test")
    assert result is not None
    assert "en.wikipedia.org/api/rest_v1/page/summary/Test" in captured["url"]


def test_encyclopedia_included_in_is_empty_and_union() -> None:
    result = LexicalResult(
        word="x", encyclopedia=(EncyclopediaEntry(title="T", summary="S", url=""),)
    )
    assert result.is_empty is False
    merged = lexical._union_results(LexicalResult(word="x"), result)
    assert merged.encyclopedia == result.encyclopedia


def test_render_lookup_includes_encyclopedia_section() -> None:
    result = LexicalResult(
        word="Ada",
        encyclopedia=(
            EncyclopediaEntry(
                title="Ada Lovelace", summary="A mathematician.", url="https://en.wikipedia.org/x"
            ),
        ),
        sources=("Wikipedia",),
    )
    text = render_lookup(result)
    assert "Encyclopedia:" in text
    assert "Ada Lovelace: A mathematician." in text
    assert "https://en.wikipedia.org/x" in text


def test_build_lookup_items_includes_encyclopedia_as_readonly() -> None:
    result = LexicalResult(
        word="Ada",
        encyclopedia=(EncyclopediaEntry(title="Ada Lovelace", summary="A mathematician.", url=""),),
    )
    items = build_lookup_items(result)
    assert items[0].kind == "encyclopedia"
    assert items[0].action == ""
    assert items[0].value == "A mathematician."


def test_normalize_source_mode_defaults_to_offline() -> None:
    assert normalize_source_mode("ONLINE") == SOURCE_ONLINE
    assert normalize_source_mode("both") == SOURCE_BOTH
    assert normalize_source_mode("nonsense") == SOURCE_OFFLINE
    assert normalize_source_mode(None) == SOURCE_OFFLINE


def test_merge_terms_ranks_agreement_first() -> None:
    merged = merge_terms([
        ("offline", ["glad", "content"]),
        ("Datamuse", ["joyful", "glad"]),
    ])
    # "glad" appears in both sources, so it ranks first.
    assert merged[0].value == "glad"
    assert merged[0].sources == ("offline", "Datamuse")
    assert merged[0].provenance == SOURCE_BOTH


def test_merge_terms_dedupes_case_insensitively_keeping_first_spelling() -> None:
    merged = merge_terms([("offline", ["Glad"]), ("Datamuse", ["glad"])])
    assert len(merged) == 1
    assert merged[0].value == "Glad"
    assert merged[0].provenance == SOURCE_BOTH


def test_merge_terms_single_source_keeps_order() -> None:
    merged = merge_terms([("offline", ["b", "a", "c"])])
    assert [item.value for item in merged] == ["b", "a", "c"]
    assert all(item.provenance == "offline" for item in merged)


def test_merge_terms_ignores_non_sequence() -> None:
    merged = merge_terms([("offline", None), ("Datamuse", ["x"])])
    assert [item.value for item in merged] == ["x"]


def test_merged_terms_for_mode_offline_only() -> None:
    merged = merged_terms_for_mode(["a"], [("Datamuse", ["b"])], mode=SOURCE_OFFLINE)
    assert [item.value for item in merged] == ["a"]
    assert merged[0].provenance == "offline"


def test_merged_terms_for_mode_online_only() -> None:
    merged = merged_terms_for_mode(["a"], [("Datamuse", ["b"])], mode=SOURCE_ONLINE)
    assert [item.value for item in merged] == ["b"]
    assert merged[0].provenance == "Datamuse"


def test_merged_terms_for_mode_both_combines() -> None:
    merged = merged_terms_for_mode(
        ["a", "shared"],
        [("Free Dictionary", ["shared", "c"])],
        mode=SOURCE_BOTH,
    )
    values = [item.value for item in merged]
    assert values[0] == "shared"  # agreement ranks first
    assert set(values) == {"a", "shared", "c"}


def test_merged_term_provenance_empty_when_no_sources() -> None:
    assert MergedTerm("x", ()).provenance == ""


# --- Accessible Look Up surface (DICT-2) -----------------------------------


def _sample_result() -> LexicalResult:
    return LexicalResult(
        word="happy",
        definitions=(
            Definition("adjective", "feeling pleasure", example="a happy child"),
            Definition("adjective", "willing"),
        ),
        synonyms=("glad", "joyful"),
        antonyms=("sad",),
        related=("cheer",),
        rhymes=("snappy",),
        sources=("Free Dictionary", "Datamuse"),
    )


def test_render_lookup_includes_word_sources_and_sections() -> None:
    text = render_lookup(_sample_result())
    assert text.startswith("Look up: happy — Free Dictionary, Datamuse")
    assert "Definitions:" in text
    assert "1. (adjective) feeling pleasure" in text
    assert "   Example: a happy child" in text
    assert "Synonyms: glad, joyful" in text
    assert "Antonyms: sad" in text
    assert "Related: cheer" in text
    assert "Rhymes: snappy" in text


def test_render_lookup_empty_result_is_not_silently_blank() -> None:
    text = render_lookup(LexicalResult(word="zzz"))
    assert "Look up: zzz" in text
    assert "No entries found." in text


def test_build_lookup_items_makes_words_insertable_and_definitions_context() -> None:
    items = build_lookup_items(_sample_result())
    definitions = [item for item in items if item.kind == "definition"]
    assert definitions and all(item.action == "" for item in definitions)
    synonyms = [item for item in items if item.kind == "synonym"]
    assert [item.value for item in synonyms] == ["glad", "joyful"]
    assert all(item.action == "insert" for item in synonyms)
    # Every word kind is represented and insertable.
    actionable = [item for item in items if item.action == "insert"]
    assert {item.kind for item in actionable} == {
        "synonym",
        "antonym",
        "related",
        "rhyme",
    }


def test_build_lookup_items_definition_label_carries_part_of_speech() -> None:
    items = build_lookup_items(_sample_result())
    first = items[0]
    assert isinstance(first, LookupItem)
    assert first.label == "adjective: feeling pleasure"


def test_build_lookup_items_empty_result_has_no_items() -> None:
    assert build_lookup_items(LexicalResult(word="zzz")) == ()
