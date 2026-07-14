"""Direct Windows SAPI 5 speech via comtypes (the pyttsx3 replacement).

QUILL drives Windows text-to-speech through the SAPI 5 ``SpVoice`` COM object
directly rather than through pyttsx3. pyttsx3's SAPI driver is a thin, fragile
wrapper around this same object whose ``runAndWait()`` reuse bug forced an
external-loop workaround, and whose ``init()`` could deadlock across threads.
Talking to ``SpVoice`` ourselves removes the dependency and gives reliable file
synthesis (``SpFileStream``) for previews and batch export.

COM threading: a ``SpVoice`` is an apartment-threaded object. comtypes calls
``CoInitializeEx`` on first use per thread, so each helper here creates and uses
its ``SpVoice`` on the calling thread. Long-lived use (the announcement worker)
must build the voice on the same thread that speaks with it -- see
``prism_bridge``.

Voice identifiers are SAPI token IDs (the registry path), which is exactly what
pyttsx3 exposed as ``voice.id`` -- so settings saved under the old engine keep
working.

Windows-only; importing on other platforms degrades to ``available() == False``.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:  # comtypes is Windows-only and is a direct dependency on Windows.
    import comtypes.client as _cc  # type: ignore[import-untyped]
except Exception:  # noqa: BLE001 - any import failure means SAPI is unavailable
    _cc = None


def _redirect_comtypes_gen_dir() -> None:
    """Point comtypes' generated-wrapper cache at a writable per-user folder.

    On first ``CreateObject("SAPI.SpVoice")`` comtypes generates Python wrappers
    for the SAPI type library and writes them to disk. Its default location is
    inside the comtypes package, which is read-only under a per-machine install
    (e.g. Program Files) -- the write fails and SAPI init raises, so QUILL falls
    back to the screen reader for no good reason. Redirect the cache to QUILL's
    writable data dir; if even that is unavailable, fall back to in-memory
    codegen (``gen_dir = None``) so SAPI still works without any disk write.
    """
    if _cc is None:
        return
    try:
        from quill.core.paths import app_data_dir

        gen_dir = app_data_dir() / "comtypes_gen"
        gen_dir.mkdir(parents=True, exist_ok=True)
        _cc.gen_dir = str(gen_dir)
    except Exception:  # noqa: BLE001 - never let cache setup break import
        try:
            _cc.gen_dir = None  # in-memory codegen; no disk write required
        except Exception:  # noqa: BLE001
            pass


_redirect_comtypes_gen_dir()

# SpFileStream.Open mode and SpeechVoiceSpeakFlags / SpeechStreamFileMode.
_SSFM_CREATE_FOR_WRITE = 3
_SVSF_IS_XML = 8  # speak the argument as SSML
# SpeechAudioFormatType: 22.05 kHz, 16-bit, mono -- a good default for speech.
_SAFT_22KHZ_16BIT_MONO = 22

_DEFAULT_RATE_WPM = 200


@dataclass(frozen=True, slots=True)
class Sapi5Voice:
    """A SAPI 5 voice: ``id`` is the token id, ``name`` the friendly description.

    ``language`` is the ISO base subtag (e.g. ``"es"``) read best-effort from the
    voice token's ``Language`` LCID attribute; ``""`` when unknown.
    """

    id: str
    name: str
    language: str = ""


# A small map from common SAPI/Windows language LCIDs (hex, lowercase) to the ISO
# 639-1 base subtag. SAPI's "Language" attribute is a hex LCID; we only need the
# primary-language nibble to pick a base language, so many region LCIDs share a base.
_LCID_BASE: dict[str, str] = {
    "9": "en",
    "a": "es",
    "c": "fr",
    "7": "de",
    "10": "it",
    "16": "pt",
    "19": "ru",
    "11": "ja",
    "12": "ko",
    "4": "zh",
    "d": "he",
    "1": "ar",
    "13": "nl",
    "8": "el",
    "e": "hu",
    "15": "pl",
    "1d": "sv",
    "5": "cs",
    "1f": "tr",
    "22": "uk",
    "2a": "vi",
    "39": "hi",
    "1e": "th",
    "6": "da",
    "b": "fi",
    "14": "no",
    "21": "id",
}


def _lcid_to_base(lcid_attr: str) -> str:
    """Map a SAPI ``Language`` LCID attribute (hex, possibly ``;``-separated) to a base."""
    first = (lcid_attr or "").split(";", 1)[0].strip().lower()
    if not first:
        return ""
    try:
        primary = int(first, 16) & 0x3FF  # primary-language id (low 10 bits)
    except ValueError:
        return ""
    return _LCID_BASE.get(format(primary, "x"), "")


def available() -> bool:
    """True when SAPI 5 can be reached (comtypes present and SpVoice creatable)."""
    if _cc is None:
        return False
    try:
        _cc.CreateObject("SAPI.SpVoice")
    except Exception:  # noqa: BLE001
        return False
    return True


def create_voice() -> Any:
    """Create a fresh ``SpVoice`` COM object on the calling thread.

    Raises :class:`RuntimeError` if SAPI cannot be reached. The object is bound
    to the calling thread's COM apartment; do not share it across threads.
    """
    if _cc is None:
        raise RuntimeError("comtypes is not available; SAPI 5 cannot be used.")
    try:
        return _cc.CreateObject("SAPI.SpVoice")
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Could not create SAPI.SpVoice: {exc}") from exc


def list_voices() -> list[Sapi5Voice]:
    """Return the installed SAPI 5 voices (empty list when SAPI is unavailable)."""
    if _cc is None:
        return []
    try:
        voice = _cc.CreateObject("SAPI.SpVoice")
        tokens = voice.GetVoices()
    except Exception:  # noqa: BLE001
        return []
    result: list[Sapi5Voice] = []
    for index in range(tokens.Count):
        token = tokens.Item(index)
        try:
            name = token.GetDescription()
        except Exception:  # noqa: BLE001
            name = token.Id
        try:
            language = _lcid_to_base(str(token.GetAttribute("Language")))
        except Exception:  # noqa: BLE001 - the attribute is optional/absent on some voices
            language = ""
        result.append(Sapi5Voice(id=token.Id, name=name, language=language))
    return result


def wpm_to_sapi_rate(rate_wpm: int) -> int:
    """Map a words-per-minute rate to SAPI's -10..10 scale.

    SAPI exposes a coarse relative rate, not WPM. 200 WPM is treated as the
    neutral 0 (matching pyttsx3's default), with roughly 20 WPM per step.
    """
    step = round((int(rate_wpm) - _DEFAULT_RATE_WPM) / 20)
    return max(-10, min(10, step))


def _select_voice(sp_voice: Any, voice_id: str) -> None:
    """Point ``sp_voice`` at the token whose Id matches ``voice_id`` (best effort)."""
    target = (voice_id or "").strip()
    if not target:
        return
    try:
        tokens = sp_voice.GetVoices()
        for index in range(tokens.Count):
            token = tokens.Item(index)
            if token.Id == target:
                sp_voice.Voice = token
                return
    except Exception:  # noqa: BLE001 - fall back to the default voice
        return


def apply_settings(
    sp_voice: Any, *, voice_id: str = "", rate_wpm: int | None = None, volume: float | None = None
) -> None:
    """Apply voice / rate / volume to an existing ``SpVoice`` (best effort)."""
    _select_voice(sp_voice, voice_id)
    if rate_wpm is not None:
        try:
            sp_voice.Rate = wpm_to_sapi_rate(rate_wpm)
        except Exception:  # noqa: BLE001
            pass
    if volume is not None:
        try:
            sp_voice.Volume = max(0, min(100, int(round(float(volume) * 100))))
        except Exception:  # noqa: BLE001
            pass


def synthesize_to_wav(
    text: str,
    output_path: Path,
    *,
    voice_id: str = "",
    rate_wpm: int = _DEFAULT_RATE_WPM,
    volume: float = 1.0,
    as_ssml: bool | None = None,
) -> None:
    """Synthesize ``text`` to a WAV file at ``output_path`` via SAPI 5.

    When *as_ssml* is true (or ``None`` and ``text`` begins with a ``<speak>``
    root) the text is spoken as W3C SSML via the ``_SVSF_IS_XML`` flag; otherwise
    as plain text. Raises :class:`RuntimeError` when SAPI is unavailable or
    synthesis fails.
    """
    if not text.strip():
        raise RuntimeError("Cannot synthesize empty text.")
    if _cc is None:
        raise RuntimeError("comtypes is not available; SAPI 5 cannot be used.")
    if as_ssml is None:
        as_ssml = text.lstrip().startswith("<speak")
    speak_flags = _SVSF_IS_XML if as_ssml else 0
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        sp_voice = _cc.CreateObject("SAPI.SpVoice")
        stream = _cc.CreateObject("SAPI.SpFileStream")
        fmt = _cc.CreateObject("SAPI.SpAudioFormat")
        fmt.Type = _SAFT_22KHZ_16BIT_MONO
        stream.Format = fmt
        stream.Open(str(output_path), _SSFM_CREATE_FOR_WRITE, False)
        try:
            apply_settings(sp_voice, voice_id=voice_id, rate_wpm=rate_wpm, volume=volume)
            sp_voice.AudioOutputStream = stream
            sp_voice.Speak(text, speak_flags)  # synchronous
        finally:
            stream.Close()
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"SAPI 5 synthesis failed: {exc}") from exc
