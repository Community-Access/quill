"""How an Ask Quill reply reaches the user: announce, text, or spoken.

Extracted from :mod:`quill.ui.assistant_panel` to keep that module under its
GATE-11 budget, and because delivery is a genuinely separate concern from the
chat panel: the panel owns the conversation, this owns what happens to an answer
once it exists.

The *policy* -- which mode wins, what degrades to what, what gets truncated --
lives in :mod:`quill.core.ai.voice_reply` and is wx-free and unit-tested. This
mixin only performs the resulting plan, which is where the wx and threading
concerns belong.
"""

from __future__ import annotations

import threading
from typing import Any


class AssistantReplyDeliveryMixin:
    """Performs a :class:`~quill.core.ai.voice_reply.VoiceReplyPlan`.

    Mixed into the Ask Quill chat panel; every attribute referenced here
    (``_wx``, ``_announce``, ``_voice_mode``, ``_open_speech_player``) is owned
    by that panel.
    """

    def _deliver_reply(self, text: str) -> None:
        """Deliver a reply the way the user configured (Voice Reply settings).

        Voice conversation mode (Alt+Shift+Q) predates the setting and has always
        spoken its answers, so while the setting is still at its default it keeps
        doing that -- entering voice mode and then being answered only in text
        would read as a regression. An explicit choice always wins.
        """
        from dataclasses import replace

        from quill.core.ai.voice_reply import plan_voice_reply

        settings = self._load_settings()
        if settings is None:
            self._announce_incoming(text)
            return
        can_speak_locally = bool(self._open_speech_player)
        if (
            self._voice_mode
            and can_speak_locally
            and getattr(settings, "ai_voice_reply_mode", "announce") == "announce"
        ):
            settings = replace(settings, ai_voice_reply_mode="local_tts")

        plan = plan_voice_reply(
            text,
            settings,
            cloud_voice_available=self._cloud_voice_ready(settings),
            local_tts_available=can_speak_locally,
        )
        if plan.fallback_reason:
            self._announce(plan.fallback_reason)
        if plan.announce_text:
            self._announce(plan.announce_text)
        if not plan.speaks:
            return
        if plan.mode == "local_tts" and self._open_speech_player:
            self._open_speech_player(plan.spoken_text)
            return
        if plan.mode == "ai_voice":
            self._speak_with_ai_voice(plan.spoken_text, settings)

    def _announce_incoming(self, text: str, *, prefix: str = "Quill says") -> None:
        """Announce *text* through the screen reader, at the configured length.

        Errors and edit proposals stay announcements whatever the reply mode --
        you do not want a 4,000-character error read out in full -- but they now
        honour the same length the user configured, instead of the literal 140
        that used to be written in here. One rule, one place.
        """
        from quill.core.ai.voice_reply import truncate_announcement

        compact = truncate_announcement(text, self._announce_limit())
        if not compact:
            return
        self._announce(f"{prefix}: {compact}")

    def _announce_limit(self) -> int:
        """The configured announcement length, read once per chat session.

        Cached because this is on the path of every announcement and reading
        settings is file I/O; the dialog is short-lived enough that changing the
        setting mid-chat and expecting it to apply to the current window is not
        a case worth a disk read per utterance.
        """
        cached = getattr(self, "_cached_announce_limit", None)
        if cached is None:
            settings = self._load_settings()
            cached = (
                int(getattr(settings, "ai_voice_reply_announce_limit", 140)) if settings else 140
            )
            self._cached_announce_limit = cached
        return int(cached)

    def _load_settings(self) -> Any:
        """Current settings, or ``None`` when they cannot be read.

        Reply delivery must never be what breaks the chat, so a settings failure
        degrades to the historical announcement rather than propagating.
        """
        try:
            from quill.core.settings import load_settings

            return load_settings()
        except Exception:  # noqa: BLE001
            return None

    def _cloud_voice_ready(self, settings: Any) -> bool:
        """True when the configured cloud TTS provider has a usable API key.

        Checked before speaking rather than after, so an unconfigured provider
        degrades to an offline voice instead of failing with the reply lost.
        """
        try:
            from quill.core.assistant_ai import load_provider_api_key

            return bool(load_provider_api_key(str(getattr(settings, "ai_tts_provider", ""))))
        except Exception:  # noqa: BLE001 - absence of a key is not an error here
            return False

    def _speak_with_ai_voice(self, text: str, settings: Any) -> None:
        """Synthesise *text* with the configured cloud voice, off the UI thread."""
        provider = str(getattr(settings, "ai_tts_provider", "openai"))

        def worker() -> None:
            try:
                from quill.core.ai.cloud_tts import default_model, default_voice, speak_text
                from quill.core.assistant_ai import load_provider_api_key

                speak_text(
                    provider,
                    text,
                    load_provider_api_key(provider),
                    model=str(getattr(settings, "ai_tts_model", "")) or default_model(provider),
                    voice=str(getattr(settings, "ai_tts_voice", "")) or default_voice(provider),
                    speed=float(getattr(settings, "ai_tts_speed", 1.0)),
                )
            except Exception as exc:  # noqa: BLE001 - never lose the reply to a TTS failure
                self._wx.CallAfter(
                    self._announce, f"Could not read the reply with the AI voice: {exc}"
                )

        threading.Thread(  # GATE-40-OK: cloud TTS worker; posts via CallAfter.
            target=worker, daemon=True
        ).start()
