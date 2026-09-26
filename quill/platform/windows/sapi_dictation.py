"""Windows speech recognition for Windows Dictation, through SAPI 5.

The recogniser is the one Windows has shipped since Vista and still ships:
``SAPI.SpInprocRecognizer`` with the dictation grammar loaded. Chosen over the
newer WinRT ``Windows.Media.SpeechRecognition`` API for three reasons that each
settle it on their own:

* **It can use the microphone you choose.** WinRT's recogniser always listens
  on the Windows default input device and offers no way to pick another; SAPI
  takes any audio-input token (``GetAudioInputs``), which is what Dictation
  Settings lists.
* **It is offline and needs no package identity.** Nothing leaves the machine,
  and there is no Store-style registration to add to the installer.
* **Nothing new to install or bundle.** It is reached through pywin32, which
  QUILL already ships; no speech model, no WinRT namespace packages.

**Threading.** The objects are apartment-threaded and deliver their events as
window messages to the thread that created them. Create a recogniser on the UI
thread and wx's own message loop delivers every event there -- so the callbacks
below run on the UI thread and may touch the editor directly, with no
``wx.CallAfter`` and no worker thread to leak.

**Privacy.** What was heard is passed to the listener and nowhere else: never
logged, never written to disk, never sent anywhere.

Windows-only; on anything else :func:`available` is ``False`` and :meth:`start`
raises :class:`~quill.core.windows_dictation.controller.DictationStartError`.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Any, Protocol

from quill.core.windows_dictation.controller import DictationStartError
from quill.core.windows_dictation.parser import RecognizedPhrase, RecognizedWord

__all__ = [
    "Microphone",
    "SapiDictationRecognizer",
    "available",
    "default_microphone_id",
    "list_microphones",
    "list_recognizers",
]

_AUDIO_INPUT_CATEGORY = r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech\AudioInput"
_RECOGNIZER_CATEGORY = r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech\Recognizers"
# SpeechLoadOption / SpeechRuleState / SpeechRecognizerState values.
_SLO_STATIC = 0
_SGDS_INACTIVE = 0
_SGDS_ACTIVE = 1
_SRS_INACTIVE_WITH_PURGE = 3
_GRAMMAR_ID = 1

_NO_ACCESS = (
    "The microphone could not be opened. Check that it is connected, and that "
    "Windows Settings, Privacy and security, Microphone lets desktop apps use it."
)


class _Listener(Protocol):
    def on_speech_started(self) -> None: ...

    def on_phrase(self, phrase: RecognizedPhrase) -> None: ...

    def on_failure(self, message: str) -> None: ...


@dataclass(frozen=True, slots=True)
class Microphone:
    """An audio input Windows can recognise speech from."""

    id: str
    name: str


def _client() -> Any:
    """``win32com.client``, or ``None`` when this is not Windows with pywin32."""
    if sys.platform != "win32":
        return None
    try:
        import win32com.client  # type: ignore[import-untyped]
    except Exception:  # noqa: BLE001 - any import failure means unavailable
        return None
    return win32com.client


def available() -> bool:
    """Whether this machine can run Windows Dictation at all."""
    client = _client()
    if client is None:
        return False
    try:
        return int(client.Dispatch("SAPI.SpInprocRecognizer").GetRecognizers().Count) > 0
    except Exception:  # noqa: BLE001 - no SAPI is an answer, not an error
        return False


def _category_default(client: Any, category: str) -> str:
    try:
        tokens = client.Dispatch("SAPI.SpObjectTokenCategory")
        tokens.SetId(category, False)
        return str(tokens.Default or "")
    except Exception:  # noqa: BLE001 - no default is an ordinary answer
        return ""


def default_microphone_id() -> str:
    """The token id of the microphone Windows itself would use, or ``""``."""
    client = _client()
    return _category_default(client, _AUDIO_INPUT_CATEGORY) if client is not None else ""


def list_microphones() -> list[Microphone]:
    """Every audio input SAPI can listen on, in Windows' order. Never raises."""
    client = _client()
    if client is None:
        return []
    try:
        tokens = client.Dispatch("SAPI.SpInprocRecognizer").GetAudioInputs()
        return [
            Microphone(str(tokens.Item(i).Id), str(tokens.Item(i).GetDescription()))
            for i in range(int(tokens.Count))
        ]
    except Exception:  # noqa: BLE001 - an empty list is the honest answer
        return []


def list_recognizers() -> list[str]:
    """The speech languages Windows speech recognition has installed, by name."""
    client = _client()
    if client is None:
        return []
    try:
        tokens = client.Dispatch("SAPI.SpInprocRecognizer").GetRecognizers()
        return [str(tokens.Item(i).GetDescription()) for i in range(int(tokens.Count))]
    except Exception:  # noqa: BLE001 - an empty list is the honest answer
        return []


def _pick(tokens: Any, wanted: str) -> Any:
    """The token *wanted* names: by id, or -- how Dictation Settings saves a
    microphone now that the other engines share the setting -- by name.

    A name is matched either way round because sounddevice's list cuts names at
    31 characters and Windows speech does not.
    """
    wanted_name = wanted.strip().lower()
    for index in range(int(tokens.Count)):
        token = tokens.Item(index)
        if str(token.Id) == wanted:
            return token
        name = str(token.GetDescription()).strip().lower()
        if name and wanted_name and (name.startswith(wanted_name) or wanted_name.startswith(name)):
            return token
    return None


def _phrase_from(result: Any) -> RecognizedPhrase:
    info = result.PhraseInfo
    words: list[RecognizedWord] = []
    elements = info.Elements
    for index in range(int(elements.Count) if elements is not None else 0):
        element = elements.Item(index)
        words.append(RecognizedWord(str(element.LexicalForm), str(element.DisplayText)))
    return RecognizedPhrase(tuple(words), text=str(info.GetText()))


def _as_dispatch(result: Any) -> Any:
    """The event's result object as something whose properties can be read."""
    client = _client()
    return client.Dispatch(result) if client is not None else result


class _EventsBase:
    """SAPI's recognition-context events, forwarded to the listener.

    pywin32 builds one class out of this and the COM object, so the listener
    rides in on a subclass made per recogniser (see
    :meth:`SapiDictationRecognizer.start`) rather than as an attribute -- an
    attribute set on the combined object would be sent to COM as a property.
    """

    _owner: SapiDictationRecognizer | None = None

    def OnSoundStart(self, *_args: Any) -> None:  # noqa: N802 - SAPI's event name
        owner = self._owner
        if owner is not None:
            owner._forward_speech_started()

    def OnRecognition(self, _stream: Any, _position: Any, _kind: Any, result: Any) -> None:  # noqa: N802
        owner = self._owner
        if owner is not None:
            owner._forward_result(result)

    def OnEndStream(self, *_args: Any) -> None:  # noqa: N802
        owner = self._owner
        if owner is not None:
            owner._forward_end()


class SapiDictationRecognizer:
    """One listening session on one microphone. Make it on the UI thread."""

    def __init__(self, listener: _Listener, *, language: str = "", pause_ms: int = 0) -> None:
        self._listener = listener
        #: How long a silence ends a phrase, in milliseconds; 0 leaves Windows'
        #: own setting alone.
        self._pause_ms = pause_ms
        #: A recogniser's name from :func:`list_recognizers`; empty for the
        #: one Windows uses by default.
        self._language = language
        self._running = False
        self._recognizer: Any = None
        self._context: Any = None
        self._grammar: Any = None
        self._stream: Any = None

    def start(self, microphone: str) -> None:
        client = _client()
        if client is None:
            raise DictationStartError(
                "Windows Dictation needs Windows speech recognition, which is not "
                "available on this computer."
            )
        try:
            # DispatchWithEvents needs the type library's generated wrappers.
            client.gencache.EnsureDispatch("SAPI.SpInprocRecognizer")
            recognizer = client.Dispatch("SAPI.SpInprocRecognizer")
            engines = recognizer.GetRecognizers()
        except Exception as error:  # noqa: BLE001 - reported, never raised raw
            raise DictationStartError(
                f"Windows speech recognition could not be started ({error})."
            ) from error
        if int(engines.Count) == 0:
            raise DictationStartError(
                "Windows has no speech recogniser installed. Add a speech language "
                "in Windows Settings, Time and language, Speech."
            )
        engine = _pick(engines, self._language) if self._language else None
        if engine is None:
            engine = _pick(engines, _category_default(client, _RECOGNIZER_CATEGORY))
        recognizer.Recognizer = engine if engine is not None else engines.Item(0)

        inputs = recognizer.GetAudioInputs()
        if int(inputs.Count) == 0:
            raise DictationStartError("No microphone was found. Connect one and try again.")
        if microphone:
            token = _pick(inputs, microphone)
            if token is None:
                raise DictationStartError(
                    f"The microphone chosen in Dictation Settings ({microphone}) is not "
                    "connected. Connect it, or choose another microphone in Dictation Settings."
                )
        else:
            token = _pick(inputs, _category_default(client, _AUDIO_INPUT_CATEGORY))
            if token is None:
                token = inputs.Item(0)
        self._activate(client, recognizer, lambda: setattr(recognizer, "AudioInput", token))

    def start_from_wav(self, path: str) -> None:
        """Recognise a WAV file instead of a microphone.

        For the integration test, which cannot speak into a microphone but can
        have Windows speak into a file; the file's end arrives as
        ``on_failure``, exactly as an unplugged microphone would.
        """
        client = _client()
        if client is None:
            raise DictationStartError("Windows speech recognition is not available.")
        client.gencache.EnsureDispatch("SAPI.SpInprocRecognizer")
        recognizer = client.Dispatch("SAPI.SpInprocRecognizer")
        recognizer.Recognizer = recognizer.GetRecognizers().Item(0)
        stream = client.Dispatch("SAPI.SpFileStream")
        stream.Open(path, 0)
        self._stream = stream
        self._activate(client, recognizer, lambda: setattr(recognizer, "AudioInputStream", stream))

    def _activate(self, client: Any, recognizer: Any, connect_input: Any) -> None:
        try:
            connect_input()
            if self._pause_ms:
                try:  # a recogniser without the property keeps its own pause
                    recognizer.SetPropertyNumber("ComplexResponseSpeed", self._pause_ms)
                except Exception:  # noqa: BLE001
                    pass
            events = type("_DictationEvents", (_EventsBase,), {"_owner": self})
            context = client.DispatchWithEvents(recognizer.CreateRecoContext(), events)
            grammar = context.CreateGrammar(_GRAMMAR_ID)
            grammar.DictationLoad("", _SLO_STATIC)
            self._recognizer, self._context, self._grammar = recognizer, context, grammar
            self._running = True
            grammar.DictationSetState(_SGDS_ACTIVE)
        except Exception as error:  # noqa: BLE001 - the microphone refused
            self.stop()
            raise DictationStartError(_NO_ACCESS) from error

    def stop(self) -> None:
        """Close the microphone. Safe to call twice, and never raises."""
        self._running = False
        grammar, context, recognizer = self._grammar, self._context, self._recognizer
        stream = self._stream
        self._grammar = self._context = self._recognizer = self._stream = None
        for step in (
            lambda: grammar.DictationSetState(_SGDS_INACTIVE),
            lambda: setattr(recognizer, "State", _SRS_INACTIVE_WITH_PURGE),
            lambda: context.close(),
            lambda: stream.Close(),
        ):
            try:
                step()
            except Exception:  # noqa: BLE001 - it is being released either way
                pass

    # -- from the events class, on the UI thread ------------------------- #

    def _forward_speech_started(self) -> None:
        if self._running:
            try:
                self._listener.on_speech_started()
            except Exception:  # noqa: BLE001 - never raise back into COM
                pass

    def _forward_result(self, result: Any) -> None:
        if not self._running:
            return
        try:
            phrase = _phrase_from(_as_dispatch(result))
        except Exception:  # noqa: BLE001 - an unreadable result is skipped
            return
        try:
            self._listener.on_phrase(phrase)
        except Exception:  # noqa: BLE001 - never raise back into COM
            pass

    def _forward_end(self) -> None:
        if not self._running:
            return
        self._running = False
        try:
            self._listener.on_failure(
                "Dictation stopped: the microphone stopped sending sound. Check that "
                "it is still connected, then start dictation again."
            )
        except Exception:  # noqa: BLE001 - never raise back into COM
            pass
