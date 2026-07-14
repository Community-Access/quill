"""Unit tests for pronunciation dictionaries (batch-document-to-speech §4.7)."""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.speech import pronunciation as pron
from quill.core.speech.pronunciation import (
    STARTER_DICTIONARY_ID,
    PronunciationDictionary,
    PronunciationEntry,
    active_dictionaries,
    apply_pronunciations,
    install_starter_dictionary,
    load_dictionaries,
    save_dictionary,
    starter_dictionary,
)


def _entry(term: str, replacement: str, **kw: object) -> PronunciationEntry:
    return PronunciationEntry(term=term, replacement=replacement, **kw)  # type: ignore[arg-type]


def _dict(id_: str, entries: list[PronunciationEntry], **kw: object) -> PronunciationDictionary:
    return PronunciationDictionary(id=id_, entries=entries, **kw)  # type: ignore[arg-type]


def test_language_scoped_dictionary_applies_only_to_its_language() -> None:
    es = _dict("es", [], language="es")
    alllangs = _dict("all", [])
    assert es.applies_to_language("es") is True
    assert es.applies_to_language("es-ES") is True  # base subtag compared
    assert es.applies_to_language("es-419") is True
    assert es.applies_to_language("en") is False
    assert alllangs.applies_to_language("en") is True  # empty = every language


def test_active_dictionaries_filters_by_language(tmp_path: Path, monkeypatch) -> None:
    es = _dict("es", [_entry("hola", "OLA")], language="es")
    en = _dict("en", [_entry("hi", "HY")], language="en")
    both = _dict("both", [_entry("ok", "OKAY")])  # no language -> all
    monkeypatch.setattr(pron, "load_dictionaries", lambda _p=None: [es, en, both])
    # Spanish synthesis: the Spanish + all-language dicts, not the English one.
    ids = {d.id for d in active_dictionaries("espeak", language="es")}
    assert ids == {"es", "both"}
    # No language filter (default): every dictionary participates (prior behavior).
    assert {d.id for d in active_dictionaries("espeak")} == {"es", "en", "both"}


def test_language_round_trips_through_dict() -> None:
    d = _dict("x", [], language="es-MX")
    # from_dict normalizes the base subtag.
    assert PronunciationDictionary.from_dict(d.to_dict()).language == "es"


# -- substitution ---------------------------------------------------------- #


def test_respelling_whole_word_substitution() -> None:
    d = _dict("g", [_entry("QUILL", "kwill")])
    out = apply_pronunciations("I love QUILL and quill alike.", "sapi5", [d])
    assert out.text == "I love kwill and kwill alike."  # case-insensitive by default
    assert out.applied == {"QUILL": 2}
    assert out.is_ssml is False


def test_whole_word_does_not_touch_substrings() -> None:
    d = _dict("g", [_entry("GIF", "jiff")])
    out = apply_pronunciations("A GIF, not GIFTED.", "sapi5", [d])
    assert out.text == "A jiff, not GIFTED."
    assert out.applied == {"GIF": 1}


def test_case_sensitive_entry() -> None:
    d = _dict("g", [_entry("It", "eye-tee", case_sensitive=True)])
    out = apply_pronunciations("It and it.", "sapi5", [d])
    assert out.text == "eye-tee and it."


def test_regex_entry() -> None:
    d = _dict("g", [_entry(r"v\d+", "version", regex=True)])
    out = apply_pronunciations("Ship v2 and v10.", "sapi5", [d])
    assert out.text == "Ship version and version."


def test_longest_term_first() -> None:
    d = _dict(
        "g",
        [_entry("New York", "noo york"), _entry("York", "yorrk")],
    )
    out = apply_pronunciations("New York", "sapi5", [d])
    assert out.text == "noo york"  # the phrase wins over the contained word


def test_disabled_entry_is_skipped() -> None:
    d_on = _dict("b", [_entry("GIF", "jiff", enabled=False)])
    out = apply_pronunciations("QUILL GIF", "sapi5", [d_on])
    assert out.text == "QUILL GIF"  # the only entry is disabled, so no change


def test_ssml_entry_uses_plain_fallback_no_raw_markup() -> None:
    d = _dict(
        "g",
        [
            _entry(
                "SQL",
                '<say-as interpret-as="characters">SQL</say-as>',
                mode="ssml",
                plain_fallback="ess cue ell",
            )
        ],
    )
    # On a non-SSML engine (Kokoro) the entry degrades to its plain fallback.
    out = apply_pronunciations("Learn SQL today.", "kokoro", [d])
    assert out.text == "Learn ess cue ell today."
    assert "<" not in out.text  # never read raw markup
    assert out.is_ssml is False


def test_ssml_entry_without_fallback_is_skipped() -> None:
    # On a non-SSML engine, an SSML entry with no fallback is skipped (not markup).
    d = _dict("g", [_entry("SQL", "<say-as>SQL</say-as>", mode="ssml", plain_fallback="")])
    out = apply_pronunciations("SQL", "kokoro", [d])
    assert out.text == "SQL"  # not substituted with raw markup


# -- precedence / scope ---------------------------------------------------- #


def test_specificity_ordering_values() -> None:
    assert _dict("p", [], scope="project", engine="sapi5").specificity() == 3
    assert _dict("p", [], scope="project").specificity() == 2
    assert _dict("g", [], engine="sapi5").specificity() == 1
    assert _dict("g", []).specificity() == 0


def test_more_specific_dictionary_wins_on_conflict() -> None:
    global_all = _dict("g", [_entry("QUILL", "global-say")])
    project_engine = _dict("p", [_entry("QUILL", "project-say")], scope="project", engine="sapi5")
    # active_dictionaries returns most-specific-first; apply dedupes keeping it.
    ordered = sorted([global_all, project_engine], key=lambda d: d.specificity(), reverse=True)
    out = apply_pronunciations("QUILL", "sapi5", ordered)
    assert out.text == "project-say"


# -- storage + resolution -------------------------------------------------- #


@pytest.fixture
def speech_home(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    monkeypatch.setattr(pron, "app_data_dir", lambda: tmp_path / "appdata")
    return tmp_path


def test_save_and_load_global(speech_home: Path) -> None:
    d = _dict("g1", [_entry("QUILL", "kwill")], name="Tech terms")
    path = save_dictionary(d)
    assert path.exists()
    loaded = load_dictionaries()
    assert len(loaded) == 1
    assert loaded[0].id == "g1"
    assert loaded[0].scope == "global"
    assert loaded[0].entries[0].term == "QUILL"


def test_project_dictionary_only_loads_with_project_dir(speech_home: Path) -> None:
    project = speech_home / "book-project"
    d = _dict("p1", [_entry("Ael", "ail")], scope="project")
    save_dictionary(d, project_dir=project)
    assert load_dictionaries() == []  # not loaded without the project dir
    loaded = load_dictionaries(project_dir=project)
    assert [x.id for x in loaded] == ["p1"]
    assert loaded[0].scope == "project"
    # stored under <project>/.quill/pronunciation/
    assert (project / ".quill" / "pronunciation" / "p1.json").exists()


def test_save_project_dictionary_without_dir_raises(speech_home: Path) -> None:
    with pytest.raises(ValueError):
        save_dictionary(_dict("p1", [], scope="project"))


def test_active_dictionaries_filters_engine_and_enabled(speech_home: Path) -> None:
    save_dictionary(_dict("all", [], name="all engines"))
    save_dictionary(_dict("sapi", [], engine="sapi5"))
    save_dictionary(_dict("piper", [], engine="piper"))
    save_dictionary(_dict("off", [], enabled=False))
    active = active_dictionaries("sapi5")
    ids = {d.id for d in active}
    assert ids == {"all", "sapi"}  # piper excluded (other engine), off excluded (disabled)


def test_active_dictionaries_enabled_ids_override(speech_home: Path) -> None:
    save_dictionary(_dict("a", [], enabled=True))
    save_dictionary(_dict("b", [], enabled=True))
    active = active_dictionaries("sapi5", enabled_ids={"a"})
    assert {d.id for d in active} == {"a"}  # explicit selection wins over the enabled flag


def test_active_dictionaries_specificity_order(speech_home: Path) -> None:
    project = speech_home / "proj"
    save_dictionary(_dict("global_all", []))
    save_dictionary(_dict("global_sapi", [], engine="sapi5"))
    save_dictionary(_dict("proj_all", [], scope="project"), project_dir=project)
    save_dictionary(_dict("proj_sapi", [], scope="project", engine="sapi5"), project_dir=project)
    order = [d.id for d in active_dictionaries("sapi5", project_dir=project)]
    assert order == ["proj_sapi", "proj_all", "global_sapi", "global_all"]


def test_dictionary_round_trips_through_dict() -> None:
    original = _dict(
        "x",
        [
            _entry("QUILL", "kwill", note="product"),
            _entry("SQL", "ess", mode="ssml", plain_fallback="ess"),
        ],
        name="N",
        scope="project",
        engine="espeak",
    )
    clone = PronunciationDictionary.from_dict(original.to_dict())
    assert clone == original


# -- starter dictionary ---------------------------------------------------- #


def test_starter_dictionary_is_global_all_engine_with_quill() -> None:
    d = starter_dictionary()
    assert d.id == STARTER_DICTIONARY_ID
    assert d.scope == "global"
    assert d.engine is None
    terms = {e.term: e.replacement for e in d.entries}
    assert terms["QUILL"] == "kwill"


def test_starter_dictionary_corrects_quill() -> None:
    out = apply_pronunciations("I use QUILL daily.", "sapi5", [starter_dictionary()])
    assert out.text == "I use kwill daily."


def test_install_starter_writes_once_and_respects_deletion(speech_home: Path) -> None:
    assert install_starter_dictionary() is True  # first install
    loaded = load_dictionaries()
    assert [d.id for d in loaded] == [STARTER_DICTIONARY_ID]
    assert install_starter_dictionary() is False  # already present → not rewritten
    assert install_starter_dictionary(overwrite=True) is True  # explicit restore


def test_starter_round_trips_through_storage(speech_home: Path) -> None:
    install_starter_dictionary()
    reloaded = load_dictionaries()[0]
    assert reloaded == starter_dictionary()


# --- SSML authoring helpers (§4.7.9) ---------------------------------------- #


def test_validate_ssml_fragment():
    from quill.core.speech.pronunciation import validate_ssml_fragment

    assert validate_ssml_fragment('<phoneme alphabet="ipa" ph="kwɪl">QUILL</phoneme>')
    assert validate_ssml_fragment('<break time="300ms"/>')
    assert validate_ssml_fragment("plain text is fine too")
    assert not validate_ssml_fragment("<bad")
    assert not validate_ssml_fragment("")


def test_ssml_fragment_builders_escape():
    from quill.core.speech.pronunciation import (
        assemble_ssml,
        engine_supports_ssml,
        ssml_break,
        ssml_phoneme,
        ssml_prosody,
        ssml_say_as,
        ssml_sub,
        validate_ssml_fragment,
    )

    # special characters in the term are escaped, keeping the fragment well-formed
    frag = ssml_sub("A&B", "A and B")
    assert "&amp;" in frag and validate_ssml_fragment(frag)
    assert ssml_phoneme("QUILL", "kwɪl").startswith("<phoneme")
    assert ssml_say_as("SQL", "characters").endswith("</say-as>")
    assert ssml_break(250) == '<break time="250ms"/>'
    assert 'rate="slow"' in ssml_prosody("x", rate="slow")
    assert validate_ssml_fragment(ssml_prosody("x", rate="slow", pitch="high"))
    assert assemble_ssml(frag) == f"<speak>{frag}</speak>"
    assert engine_supports_ssml("sapi5") and engine_supports_ssml("espeak")
    assert not engine_supports_ssml("kokoro")


def test_apply_pronunciations_emits_ssml_on_capable_engine():
    from quill.core.speech.pronunciation import (
        PronunciationDictionary,
        PronunciationEntry,
        apply_pronunciations,
        validate_ssml_fragment,
    )

    dicts = [
        PronunciationDictionary(
            id="d",
            entries=[
                PronunciationEntry(
                    term="SQL",
                    replacement='<sub alias="sequel">SQL</sub>',
                    mode="ssml",
                    plain_fallback="sequel",
                )
            ],
        )
    ]
    # SAPI 5 is SSML-capable: the utterance becomes a <speak> with the raw fragment
    r = apply_pronunciations("Learn SQL & more.", "sapi5", dicts)
    assert r.is_ssml is True
    assert r.text.startswith("<speak>") and r.text.endswith("</speak>")
    assert '<sub alias="sequel">SQL</sub>' in r.text
    assert "&amp; more" in r.text  # surrounding text is XML-escaped
    assert validate_ssml_fragment(r.text)

    # Kokoro is not SSML-capable: the plain fallback is spoken, no markup
    r2 = apply_pronunciations("Learn SQL & more.", "kokoro", dicts)
    assert r2.is_ssml is False
    assert r2.text == "Learn sequel & more."


def test_apply_pronunciations_ssml_falls_back_when_malformed():
    from quill.core.speech.pronunciation import (
        PronunciationDictionary,
        PronunciationEntry,
        apply_pronunciations,
    )

    dicts = [
        PronunciationDictionary(
            id="d",
            entries=[
                PronunciationEntry(
                    term="X", replacement="<broken", mode="ssml", plain_fallback="ex"
                )
            ],
        )
    ]
    r = apply_pronunciations("an X here", "sapi5", dicts)
    assert r.is_ssml is False  # malformed SSML -> plain fallback
    assert r.text == "an ex here"
