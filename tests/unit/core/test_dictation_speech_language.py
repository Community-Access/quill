"""Spanish dictation (dict.md section 9): the language setting and everything it reaches.

All with fakes: no microphone, no speech model, no network. What is checked is
that the language flows -- to the model, the model cache, filler removal, the
wake and stop phrases, the punctuation words, the command table behind its
flag, and Windows speech recognition's choice of recogniser.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from quill.core.windows_dictation import engines, local_recognizer
from quill.core.windows_dictation.composer import compose
from quill.core.windows_dictation.controller import DictationController, DictationStartError
from quill.core.windows_dictation.options import clean_phrase
from quill.core.windows_dictation.parser import RecognizedPhrase, parse, words_from_text
from quill.core.windows_dictation.preferences import DictationPreferences
from quill.core.windows_dictation.reference import commands_reference
from quill.core.windows_dictation.settings_fields import load_fields
from quill.core.windows_dictation.speech_language import (
    SPANISH_COMMANDS_VARIABLE,
    coerce_speech_language,
    fold,
    localised_phrase,
    spanish_commands_enabled,
)
from quill.core.windows_dictation.vocabulary import ENGLISH, Command, vocabulary_for
from quill.core.windows_dictation.wake import STOP_PHRASES, WAKE_PHRASES, match_wake, wake_words

_OPEN_Q = chr(0xBF)


def _phrase(text: str) -> RecognizedPhrase:
    return RecognizedPhrase(words_from_text(text), text=text)


def _spanish(text: str, *, marks: bool = True, before: str = "") -> str:
    vocabulary = vocabulary_for("es", spoken_marks=marks)
    return compose(parse(_phrase(text), vocabulary=vocabulary).pieces, before=before)


# --------------------------------------------------------------------------- #
# The setting
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("saved", "expected"),
    [("es", "es"), ("es-MX", "es"), ("Spanish", "es"), ("en", "en"), ("", "en"), ("fr", "en")],
)
def test_the_language_setting_is_coerced(saved: str, expected: str) -> None:
    assert coerce_speech_language(saved) == expected
    assert (
        load_fields({"windows_dictation_speech_language": saved})[
            "windows_dictation_speech_language"
        ]
        == expected
    )


def test_english_is_the_default_everywhere() -> None:
    from quill.core.lite.settings import Settings as LiteSettings
    from quill.core.settings import Settings

    assert Settings().windows_dictation_speech_language == "en"
    assert LiteSettings().windows_dictation_speech_language == "en"
    assert load_fields({})["windows_dictation_speech_language"] == "en"
    assert DictationPreferences.from_settings(object()).speech_language == "en"


def test_quill_saves_and_loads_the_language(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    from quill.core.settings import Settings, load_settings, save_settings

    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    save_settings(Settings(windows_dictation_speech_language="es"))
    assert load_settings().windows_dictation_speech_language == "es"


def test_quill_lite_saves_and_loads_the_language(tmp_path: Path) -> None:
    from quill.core.lite import settings as lite

    path = tmp_path / "settings.json"
    lite.save(lite.Settings(windows_dictation_speech_language="es"), path)
    assert lite.load(path).windows_dictation_speech_language == "es"


# --------------------------------------------------------------------------- #
# The model, and the cache
# --------------------------------------------------------------------------- #


def test_spanish_uses_multilingual_whisper_whichever_built_in_engine_is_chosen() -> None:
    assert engines.model_for("moonshine", "en").id == "moonshine"
    assert engines.model_for("whisper", "en").folder == "whisper-tiny-en"
    for engine in ("moonshine", "whisper"):
        assert engines.model_for(engine, "es") is engines.WHISPER_MULTILINGUAL
    assert engines.model_for("windows", "es").id == "windows"


def test_the_multilingual_model_is_pinned_and_fetched_like_the_others() -> None:
    model = engines.WHISPER_MULTILINGUAL
    assert model.archive.endswith("sherpa-onnx-whisper-tiny.tar.bz2")
    assert {item.name for item in model.files} == {
        "encoder.int8.onnx",
        "decoder.int8.onnx",
        "tokens.txt",
    }
    assert all(len(item.sha256) == 64 for item in model.files)
    assert model in engines.LANGUAGE_MODELS and model not in engines.ENGINES
    folders = [e.folder for e in engines.ENGINES + engines.LANGUAGE_MODELS if e.folder]
    assert len(folders) == len(set(folders))


def test_a_missing_spanish_model_is_said_plainly(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(engines, "model_roots", lambda: [tmp_path])
    problem = engines.language_model_problem("moonshine", "es")
    assert "Spanish" in problem and "Reinstalling" in problem
    assert engines.language_model_problem("moonshine", "en") == ""
    assert engines.language_model_problem("windows", "es") == ""
    for item in engines.WHISPER_MULTILINGUAL.files:
        folder = tmp_path / "whisper-tiny"
        folder.mkdir(exist_ok=True)
        (folder / item.name).write_bytes(b"x")
    assert engines.language_model_problem("whisper", "es") == ""


class _Sherpa:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        outer = self

        class OfflineRecognizer:
            @staticmethod
            def from_whisper(**kwargs: Any) -> object:
                outer.calls.append(kwargs)
                return object()

            @staticmethod
            def from_moonshine(**kwargs: Any) -> object:
                outer.calls.append({"moonshine": True, **kwargs})
                return object()

        self.OfflineRecognizer = OfflineRecognizer


def test_whisper_is_loaded_with_the_language_and_cached_per_language(monkeypatch, tmp_path) -> None:
    sherpa = _Sherpa()
    folders: list[tuple[str, str]] = []

    def model_dir(engine: str, language: str = "en") -> Path:
        folders.append((engine, language))
        return tmp_path

    monkeypatch.setattr(local_recognizer, "_import_sherpa", lambda: sherpa)
    monkeypatch.setattr(local_recognizer, "model_dir", model_dir)
    monkeypatch.setattr(local_recognizer, "_recognizers", {})

    spanish = local_recognizer._load("moonshine", "es")
    assert sherpa.calls[-1]["language"] == "es"
    assert "moonshine" not in sherpa.calls[-1]  # Moonshine has no Spanish
    assert local_recognizer._load("moonshine", "es") is spanish  # cached
    english = local_recognizer._load("moonshine", "en")
    assert english is not spanish and sherpa.calls[-1].get("moonshine")
    local_recognizer._load("whisper", "en")
    assert sherpa.calls[-1]["language"] == "en"
    assert set(local_recognizer._recognizers) == {
        ("moonshine", "es"),
        ("moonshine", "en"),
        ("whisper", "en"),
    }


def test_the_recogniser_transcribes_in_its_language(monkeypatch) -> None:
    heard: list[tuple[str, str]] = []

    def transcribe(engine: str, _samples: Any, language: str = "en") -> str:
        heard.append((engine, language))
        return "hola"

    monkeypatch.setattr(local_recognizer, "transcribe", transcribe)
    engine = local_recognizer.LocalDictationRecognizer(
        object(),  # type: ignore[arg-type]
        "whisper",
        post=lambda f, *a: f(*a),
        language="es",
    )
    assert engine._transcribe_healing([0.0]) == "hola"
    assert heard == [("whisper", "es")]


# --------------------------------------------------------------------------- #
# Fillers, wake and stop
# --------------------------------------------------------------------------- #


def test_filler_removal_is_told_the_language() -> None:
    spanish = DictationPreferences(engine="whisper", speech_language="es")
    english = DictationPreferences(engine="whisper")
    assert spanish.filler_language == "es" and english.filler_language == "en"
    assert DictationPreferences(engine="windows").filler_language == ""
    assert DictationPreferences(engine="windows", speech_language="es").filler_language == "es"

    def cleaned(text: str, language: str) -> str:
        phrase = clean_phrase(
            _phrase(text), remove_fillers=True, strip_punctuation=False, language=language
        )
        return phrase.text

    assert cleaned("eh este libro es bueno", "es") == "este libro es bueno"
    assert cleaned("um this is good", "en") == "this is good"
    assert cleaned("um es bueno", "es") == "um es bueno"  # "um" is not a Spanish filler


def test_wake_and_stop_phrases_follow_the_language() -> None:
    class Spanish:
        windows_dictation_speech_language = "es"

    preferences = DictationPreferences.from_settings(Spanish())
    assert preferences.wake_phrase == WAKE_PHRASES["es"] == "Quill dicta"
    assert preferences.stop_phrase == STOP_PHRASES["es"] == "deja de dictar"

    class Custom(Spanish):
        windows_dictation_wake_phrase = "hola pluma"

    assert DictationPreferences.from_settings(Custom()).wake_phrase == "hola pluma"
    assert localised_phrase("Quill dicta", "en", WAKE_PHRASES) == "Quill dictate"
    assert localised_phrase("", "es", STOP_PHRASES) == "deja de dictar"


def test_wake_matching_ignores_accents_and_marks() -> None:
    assert wake_words(f"{_OPEN_Q}Quill, díctá?") == ["quill", "dicta"]
    assert match_wake(wake_words("Quill dicta hola"), "Quill dicta") == 2
    assert fold("Línea Año") == "linea ano"


class _Document:
    def __init__(self) -> None:
        self.text = ""

    def unavailable_reason(self, *, writing: bool) -> str:
        return ""

    def context(self) -> tuple[str, str]:
        return self.text, ""

    def insert(self, text: str) -> tuple[int, int]:
        start = len(self.text)
        self.text += text
        return start, len(self.text)

    def selection(self) -> tuple[int, int]:
        return len(self.text), len(self.text)


class _Feedback:
    def __init__(self) -> None:
        self.said: list[str] = []

    def has_cue(self, _moment: Any) -> bool:
        return False

    def cue(self, _moment: Any) -> None: ...

    def say(self, text: str) -> None:
        self.said.append(text)

    def read_back(self, text: str) -> None: ...

    def show(self, text: str) -> None: ...

    def state_changed(self, _state: Any) -> None: ...

    def show_commands(self) -> None: ...


class _Recognizer:
    def start(self, _microphone: str) -> None: ...

    def stop(self) -> None: ...


def _session(**preferences: Any) -> tuple[DictationController, _Document]:
    document = _Document()
    chosen = DictationPreferences(speech_language="es", **preferences)
    controller = DictationController(
        recognizer=lambda _c, _p: _Recognizer(),
        document=document,  # type: ignore[arg-type]
        feedback=_Feedback(),  # type: ignore[arg-type]
        preferences=lambda: chosen,
    )
    return controller, document


def test_spanish_wake_phrase_wakes_and_the_rest_is_written() -> None:
    controller, document = _session(wake_enabled=True, wake_phrase="Quill dicta")
    controller.arm()
    controller.on_phrase(_phrase("Quill dicta hola amigos"))
    assert controller.active
    assert document.text == "Hola amigos"


def test_spanish_stop_phrase_stops() -> None:
    controller, _document = _session(stop_phrase="deja de dictar")
    controller.start()
    controller.on_phrase(_phrase("Deja de dictar."))
    assert not controller.active


# --------------------------------------------------------------------------- #
# Punctuation words: only while the engine is not punctuating (option 1)
# --------------------------------------------------------------------------- #


def test_coma_and_punto_write_marks_with_automatic_punctuation_off() -> None:
    controller, document = _session(engine="whisper", auto_punctuation=False)
    controller.start()
    controller.on_phrase(_phrase("hola coma qué tal punto"))
    assert document.text == "Hola, qué tal."


def test_coma_and_punto_are_words_with_automatic_punctuation_on() -> None:
    controller, document = _session(engine="whisper", auto_punctuation=True)
    controller.start()
    controller.on_phrase(_phrase("que coma el punto es que"))
    assert document.text == "Que coma el punto es que"


def test_windows_speech_never_punctuates_so_the_words_always_count() -> None:
    controller, document = _session(engine="windows")
    controller.start()
    controller.on_phrase(_phrase("hola coma amigos"))
    assert document.text == "Hola, amigos"


def test_spanish_marks_match_with_or_without_accents() -> None:
    assert _spanish("hola nueva línea adiós") == "Hola\nAdiós"
    assert _spanish("hola nueva linea adiós") == "Hola\nAdiós"
    assert _spanish("dos puntos") == ":"
    assert _spanish("punto y aparte") == ".\n\n"
    assert _spanish("hola punto y coma adiós") == "Hola; adiós"


def test_inverted_marks_open_and_the_next_word_takes_its_capital() -> None:
    said = "abrir interrogación qué tal cerrar interrogación"
    assert _spanish(said) == f"{_OPEN_Q}Qué tal?"
    assert _spanish("hola abrir exclamación qué bien cerrar exclamación") == (
        f"Hola {chr(0xA1)}qué bien!"
    )
    # Said as a phrase of its own, then the question in the next one.
    assert _spanish("qué tal", before=f"Hola. {_OPEN_Q}") == "Qué tal"


def test_literal_writes_the_word_with_its_accents() -> None:
    assert _spanish("literal coma") == "Coma"
    assert _spanish("literal nueva línea") == "Nueva línea"


def test_spanish_words_that_look_like_english_marks_stay_words() -> None:
    assert _spanish("el Colón") == "El Colón"
    assert _spanish("el colon") == "El colon"
    # English keeps "colon", and is untouched by Spanish.
    assert compose(parse(_phrase("note colon")).pieces) == "Note:"


def test_english_marks_still_work_in_spanish_text() -> None:
    assert _spanish("hola comma amigos", marks=False) == "Hola, amigos"
    assert _spanish("hola coma amigos", marks=False) == "Hola coma amigos"


def test_accented_words_survive_into_the_text() -> None:
    assert _spanish("mañana iré al café") == "Mañana iré al café"


# --------------------------------------------------------------------------- #
# The drafted command table: off unless a development build asks for it
# --------------------------------------------------------------------------- #


def test_the_spanish_commands_are_off_by_default(monkeypatch) -> None:
    monkeypatch.delenv(SPANISH_COMMANDS_VARIABLE, raising=False)
    assert not spanish_commands_enabled()
    parsed = parse(_phrase("borra eso"), vocabulary=vocabulary_for("es"))
    assert parsed.command is None
    # The English commands are what ships: "scratch that" works in Spanish.
    assert parse(_phrase("scratch that"), vocabulary=vocabulary_for("es")).command is (
        Command.SCRATCH
    )


def test_the_spanish_commands_need_a_development_build(monkeypatch) -> None:
    from quill.core import paths

    monkeypatch.setenv(SPANISH_COMMANDS_VARIABLE, "1")
    monkeypatch.setattr(paths, "_DEV_BUILD", False)
    assert not spanish_commands_enabled()
    monkeypatch.setattr(paths, "_DEV_BUILD", True)
    assert spanish_commands_enabled()


def test_the_spanish_commands_work_when_switched_on(monkeypatch) -> None:
    from quill.core import paths

    monkeypatch.setattr(paths, "_DEV_BUILD", True)
    monkeypatch.setenv(SPANISH_COMMANDS_VARIABLE, "1")
    vocabulary = vocabulary_for("es")
    assert parse(_phrase("Borra eso."), vocabulary=vocabulary).command is Command.SCRATCH
    assert parse(_phrase("deshacer"), vocabulary=vocabulary).command is Command.UNDO
    assert parse(_phrase("ir al final de la línea"), vocabulary=vocabulary).command is (
        Command.LINE_END
    )
    assert parse(_phrase("ir al final de la linea"), vocabulary=vocabulary).command is (
        Command.LINE_END
    )
    assert parse(_phrase("qué puedo decir"), vocabulary=vocabulary).command is Command.HELP
    # A command inside a sentence is words, as in English.
    sentence = parse(_phrase("dijo borra eso ahora"), vocabulary=vocabulary)
    assert sentence.command is None
    # Spelling understands the Spanish capital.
    spelled = parse(_phrase("mayúscula alfa bravo"), spelling=True, vocabulary=vocabulary)
    assert spelled.pieces[0].text == "Ab"
    assert "SPANISH COMMANDS" in commands_reference(language="es")


def test_english_is_never_affected() -> None:
    assert vocabulary_for("en") is ENGLISH
    assert vocabulary_for("en", spoken_marks=False) is ENGLISH
    assert parse(_phrase("coma")).pieces[0].mark is None


def test_the_commands_list_adds_spanish_punctuation_only_in_spanish(monkeypatch) -> None:
    monkeypatch.delenv(SPANISH_COMMANDS_VARIABLE, raising=False)
    english = commands_reference()
    spanish = commands_reference(language="es")
    assert "SPANISH PUNCTUATION" not in english
    assert "SPANISH PUNCTUATION" in spanish and '"coma": ,' in spanish
    assert "SPANISH COMMANDS" not in spanish
    assert commands_reference(markdown=True) == commands_reference(markdown=True, language="en")


# --------------------------------------------------------------------------- #
# Windows speech recognition: a Spanish recogniser, or a plain sentence
# --------------------------------------------------------------------------- #


class _Token:
    def __init__(self, name: str, language: str) -> None:
        self.Id = "HKEY_" + name
        self._name, self._language = name, language

    def GetDescription(self) -> str:  # noqa: N802 - SAPI's name
        return self._name

    def GetAttribute(self, _name: str) -> str:  # noqa: N802
        return self._language


class _Tokens:
    def __init__(self, *tokens: _Token) -> None:
        self._tokens = tokens
        self.Count = len(tokens)

    def Item(self, index: int) -> _Token:  # noqa: N802
        return self._tokens[index]


def test_sapi_picks_a_spanish_recogniser() -> None:
    from quill.platform.windows.sapi_dictation import pick_for_language

    english = _Token("Microsoft Speech Recognizer 8.0 for Windows (English - US)", "409")
    mexico = _Token("Microsoft Speech Recognizer 8.0 for Windows (Spanish - Mexico)", "80A")
    spain = _Token("Microsoft Speech Recognizer 8.0 for Windows (Spanish - Spain)", "C0A")
    tokens = _Tokens(english, mexico, spain)
    assert pick_for_language(tokens, "es") is mexico
    assert pick_for_language(tokens, "es", spain._name) is spain
    assert pick_for_language(tokens, "es", english._name) is mexico  # not Spanish: passed over
    assert pick_for_language(_Tokens(english), "es") is None
    assert pick_for_language(tokens, "en") is None  # Windows' default, as before
    assert pick_for_language(tokens, "en", english._name) is english


def test_sapi_says_plainly_when_windows_has_no_spanish(monkeypatch) -> None:
    from quill.platform.windows import sapi_dictation

    english = _Token("Microsoft Speech Recognizer (English - US)", "409")

    class Recognizer:
        def GetRecognizers(self) -> _Tokens:  # noqa: N802
            return _Tokens(english)

    class Client:
        class gencache:  # noqa: N801 - pywin32's name
            @staticmethod
            def EnsureDispatch(_name: str) -> None: ...  # noqa: N802

        @staticmethod
        def Dispatch(_name: str) -> Recognizer:  # noqa: N802
            return Recognizer()

    monkeypatch.setattr(sapi_dictation, "_client", lambda: Client)
    recognizer = sapi_dictation.SapiDictationRecognizer(object(), speech_language="es")  # type: ignore[arg-type]
    with pytest.raises(DictationStartError) as caught:
        recognizer.start("")
    assert "no Spanish speech recogniser" in str(caught.value)
