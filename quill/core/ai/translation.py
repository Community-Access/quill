"""AI-powered inline translation for QUILL.

Supports cloud translation via the configured AI provider (OpenAI, Claude, etc.)
and optional local LibreTranslate for privacy-sensitive workflows.
"""

from __future__ import annotations

import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from quill.core.ai.custom_instructions import split_instruction
from quill.core.assistant_ai import AssistantConnectionSettings, generate_assistant_response
from quill.core.error_codes import CodedError
from quill.core.net import verified_ssl_context

SUPPORTED_LANGUAGES: dict[str, str] = {
    "Afrikaans": "af",
    "Arabic": "ar",
    "Bulgarian": "bg",
    "Chinese (Simplified)": "zh",
    "Chinese (Traditional)": "zh-TW",
    "Croatian": "hr",
    "Czech": "cs",
    "Danish": "da",
    "Dutch": "nl",
    "English": "en",
    "Estonian": "et",
    "Finnish": "fi",
    "French": "fr",
    "German": "de",
    "Greek": "el",
    "Hebrew": "he",
    "Hindi": "hi",
    "Hungarian": "hu",
    "Indonesian": "id",
    "Italian": "it",
    "Japanese": "ja",
    "Korean": "ko",
    "Latvian": "lv",
    "Lithuanian": "lt",
    "Norwegian": "no",
    "Polish": "pl",
    "Portuguese (Brazil)": "pt-BR",
    "Portuguese (Portugal)": "pt",
    "Romanian": "ro",
    "Russian": "ru",
    "Slovak": "sk",
    "Slovenian": "sl",
    "Spanish": "es",
    "Swedish": "sv",
    "Thai": "th",
    "Turkish": "tr",
    "Ukrainian": "uk",
    "Vietnamese": "vi",
}

LANGUAGE_NAMES: dict[str, str] = {code: name for name, code in SUPPORTED_LANGUAGES.items()}

_TRANSLATE_PROMPT_TEMPLATE = (
    "Translate the following text into {target_language}. "
    "Before the translation, output a JSON line on its own: "
    '{{"source": "<detected ISO 639-1 code>"}}\n'
    "Then output the translation on the next line(s). "
    "Preserve formatting, tone, and paragraph structure exactly. "
    "Return only the JSON detection line and the translated text - no commentary.\n\n"
    "TEXT TO TRANSLATE:\n"
)


class TranslationError(CodedError):
    code = "QUILL-AI-TRANSLATE-FAILED"


class TranslationAuthError(TranslationError):
    pass


def translate_text(
    text: str,
    target_language: str,
    connection: AssistantConnectionSettings,
    api_key: str = "",
    provider: str = "ai_assistant",
    libretranslate_url: str = "http://localhost:5000",
    *,
    markdown: bool = False,
    source_language: str = "",
) -> tuple[str, str]:
    """Translate *text* to *target_language*.

    *provider*: "ai_assistant" (default, uses configured AI) or "libretranslate".
    *source_language* names the language the text is in (a name or an ISO code);
    empty, or :data:`SOURCE_DETECT`, lets the translator detect it.
    *markdown* says the text is Markdown: the preservation clause is then added
    even when the user has replaced Translate's default instruction.

    Returns (translated_text, detected_source_language).
    detected_source_language is an ISO 639-1 code or "unknown".
    """
    if not text.strip():
        raise TranslationError("No text to translate.")

    target_name = _resolve_target_name(target_language)
    source = "" if source_language in ("", SOURCE_DETECT) else source_language

    if provider == "libretranslate":
        return _translate_libretranslate(
            text, target_language, libretranslate_url, source=_source_code(source)
        )

    return _translate_ai(
        text,
        target_name,
        connection,
        api_key,
        markdown=markdown,
        source_name=_resolve_target_name(source) if source else "",
    )


def _source_code(source: str) -> str:
    """An ISO code for *source*, or "" for Detect."""
    if not source:
        return ""
    return SUPPORTED_LANGUAGES.get(source, source)


UNCHANGED_TRANSLATION_MESSAGE = (
    "The translation came back the same as the original. "
    "The source language may be wrong; choose it instead of Detect."
)

#: The free AI's Translate (both editors' AI pad) takes a target language only,
#: so there is no Detect to change there; the advice is what can be done.
HOSTED_UNCHANGED_TRANSLATION_MESSAGE = (
    "The translation came back the same as the original. The text may already "
    "be in the language you chose, or the AI could not tell what language it is in."
)

#: The first row of every Translate from list: let the translator work it out.
SOURCE_DETECT = "Detect"


def _comparable(text: str) -> str:
    return " ".join(text.split()).casefold()


def translation_unchanged(original: str, translated: str) -> bool:
    """True when *translated* is just *original* handed back.

    Whitespace runs collapse and case is ignored, so a result that differs only
    in line wrapping or capitalisation still counts as the same text. That is
    what comes back when the source was already in the target language, and
    calling it a translation would hide that nothing was translated. Empty text
    on either side is never "unchanged": that is a failure, reported elsewhere.
    """
    a = _comparable(original)
    b = _comparable(translated)
    return bool(a) and a == b


def _resolve_target_name(target: str) -> str:
    """Accept either a language name or ISO code, return the display name."""
    if target in SUPPORTED_LANGUAGES:
        return target
    if target in LANGUAGE_NAMES:
        return LANGUAGE_NAMES[target]
    return target


def _translate_ai(
    text: str,
    target_language_name: str,
    connection: AssistantConnectionSettings,
    api_key: str,
    *,
    markdown: bool = False,
    source_name: str = "",
) -> tuple[str, str]:
    template = _TRANSLATE_PROMPT_TEMPLATE.format(target_language=target_language_name)
    if source_name:
        # Named by the person: say so, so the model translates rather than
        # deciding the text is already in the target language.
        template = template.replace(
            "Translate the following text into",
            f"The following text is in {source_name}. Translate it into",
            1,
        )
    system_prompt, user_prompt = split_instruction("translate", template + text, markdown=markdown)
    response, error = generate_assistant_response(
        connection,
        api_key,
        user_prompt,
        max_tokens=8192,
        timeout_seconds=120.0,
        system_prompt=system_prompt,
    )
    if error:
        msg = error.lower()
        if "auth" in msg or "401" in msg:
            raise TranslationAuthError(error)
        raise TranslationError(error)
    if not response:
        raise TranslationError("AI returned no response.")

    return _parse_translation_response(response)


def _parse_translation_response(response: str) -> tuple[str, str]:
    """Parse the detection JSON line and translation from the AI response."""
    lines = response.strip().splitlines()
    source_lang = "unknown"
    translation_lines: list[str] = []

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("{") and '"source"' in stripped:
            try:
                data = json.loads(stripped)
                source_lang = str(data.get("source", "unknown")).strip()
                translation_lines = lines[i + 1 :]
                break
            except json.JSONDecodeError:
                translation_lines = lines
                break
    else:
        translation_lines = lines

    translation = "\n".join(translation_lines).strip()
    return translation, source_lang


def _translate_libretranslate(
    text: str,
    target: str,
    base_url: str,
    *,
    source: str = "",
) -> tuple[str, str]:
    """Translate via a local LibreTranslate instance (*source* is an ISO code, or "")."""
    endpoint = base_url.rstrip("/") + "/translate"
    # Detect source language first, unless the person named it
    detect_endpoint = base_url.rstrip("/") + "/detect"
    source_lang = source or "auto"
    try:
        if source:
            raise LookupError("named, so not detected")
        detect_body = json.dumps({"q": text[:500]}).encode()
        req = Request(
            detect_endpoint,
            data=detect_body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        ctx = verified_ssl_context()
        with urlopen(req, context=ctx, timeout=15) as resp:
            detected = json.loads(resp.read())
            if isinstance(detected, list) and detected:
                source_lang = detected[0].get("language", "auto")
    except Exception:  # noqa: BLE001
        pass

    payload = json.dumps({
        "q": text,
        "source": source_lang if source_lang != "auto" else "auto",
        "target": target if len(target) == 2 else SUPPORTED_LANGUAGES.get(target, "en"),
        "format": "text",
    }).encode()
    req = Request(
        endpoint,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        ctx = verified_ssl_context()
        with urlopen(req, context=ctx, timeout=60) as resp:
            result = json.loads(resp.read())
            translated = result.get("translatedText", "")
            return translated, source_lang
    except HTTPError as exc:
        raise TranslationError(f"LibreTranslate HTTP {exc.code}") from exc
    except Exception as exc:
        raise TranslationError(f"LibreTranslate error: {exc}") from exc
