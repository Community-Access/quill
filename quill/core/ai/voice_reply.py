"""How an AI chat reply comes back when the question was asked by voice.

Ask Quill has always had the voice round-trip -- Ctrl+F9 records, QUILL
transcribes offline, the model answers -- but the answer only ever came back one
way: a short summary handed to the screen reader. Meanwhile QUILL already had
two full speech stacks that could have read it properly, its own offline voices
and the cloud AI voices in :mod:`quill.core.ai.cloud_tts`. They were wired to
document read-aloud and nothing else. This module is the missing join.

It is deliberately a *decision* layer, not a speaking layer: it takes the reply
text and the user's settings and returns a :class:`VoiceReplyPlan` saying what
should happen. The UI performs it. That keeps the policy -- which is where the
interesting rules live -- wx-free, synchronous, and unit-testable, and keeps the
"speak this / show this" mechanics where they belong.

Two rules are worth stating outright, because they are the ones a user would be
annoyed to discover by accident:

* **Cloud voices are opt-in and never a silent upgrade.** ``ai_voice`` bills per
  character and sends the reply text to OpenAI/Gemini. Nothing selects it on a
  user's behalf, and when it cannot be used the fallback is always *more*
  private, never less.
* **Truncation belongs to announcements only.** A 140-character cap is right for
  a screen-reader summary and wrong for speech -- reading the first 137
  characters of an answer aloud and stopping is worse than not reading it.
"""

from __future__ import annotations

from dataclasses import dataclass

from quill.core.settings import VOICE_REPLY_MODES, Settings

__all__ = [
    "VOICE_REPLY_MODES",
    "VoiceReplyPlan",
    "mode_label",
    "plan_voice_reply",
    "truncate_announcement",
]

#: Providers :mod:`quill.core.ai.cloud_tts` can *speak* with. ElevenLabs is in
#: that module's catalog for audio export only, so choosing it for a spoken
#: reply has to degrade rather than fail at the moment of speaking.
_SPEAKABLE_CLOUD_PROVIDERS = frozenset({"openai", "gemini"})

_MODE_LABELS = {
    "announce": "a short spoken summary",
    "text": "text only",
    "local_tts": "read aloud with QUILL's own voice",
    "ai_voice": "read aloud with the AI voice",
}


def mode_label(mode: str) -> str:
    """Human phrasing for *mode*, for confirmations and the settings summary."""
    return _MODE_LABELS.get(mode, mode)


@dataclass(frozen=True, slots=True)
class VoiceReplyPlan:
    """What the UI should do with one reply.

    ``spoken_text`` is empty when nothing should be spoken. ``announce_text`` is
    the screen-reader announcement, already truncated when that applies. The two
    are mutually exclusive by construction: speaking a reply *and* announcing it
    would talk over itself.
    """

    mode: str
    announce_text: str = ""
    spoken_text: str = ""
    #: Set when the requested mode could not be honoured, e.g. a cloud voice
    #: with no API key. Worth telling the user once -- silently doing something
    #: other than what they configured is how trust in a setting is lost.
    fallback_reason: str = ""

    @property
    def speaks(self) -> bool:
        return bool(self.spoken_text)

    @property
    def uses_cloud(self) -> bool:
        return self.mode == "ai_voice" and bool(self.spoken_text)


def truncate_announcement(text: str, limit: int) -> str:
    """Collapse whitespace and cap at *limit* characters (0 = no cap).

    The one truncation rule every screen-reader announcement in the chat shares
    -- replies, errors, and edit proposals alike. It used to be a literal 140
    written into the announcement helper, which meant the user's configured
    length governed replies while errors and proposals silently kept the old
    number.

    Truncation is for *announcements* specifically: they are transient and
    interruptible, so brevity is a feature there. Spoken replies are never cut
    (see :func:`plan_voice_reply`).
    """
    compact = " ".join((text or "").split())
    if limit <= 0 or len(compact) <= limit:
        return compact
    return compact[: max(1, limit - 3)].rstrip() + "..."


def plan_voice_reply(
    text: str,
    settings: Settings,
    *,
    cloud_voice_available: bool = True,
    local_tts_available: bool = True,
    announce_prefix: str = "Quill says",
) -> VoiceReplyPlan:
    """Decide how *text* should be delivered, honouring *settings*.

    ``cloud_voice_available`` / ``local_tts_available`` let the caller report
    what actually works right now (an API key present, a voice installed). When
    the configured mode is unavailable the plan degrades **towards** the offline
    default rather than failing, and records why in ``fallback_reason`` so the
    UI can say so once instead of leaving the user wondering why their setting
    appears to be ignored.

    An empty reply produces an empty plan: there is nothing to say, and an
    announcement of "" is just noise.
    """
    compact = " ".join((text or "").split())
    if not compact:
        return VoiceReplyPlan(mode=settings.ai_voice_reply_mode)

    mode = settings.ai_voice_reply_mode
    if mode not in VOICE_REPLY_MODES:  # defensive: settings validate, callers may not
        mode = "announce"

    reason = ""
    if mode == "ai_voice":
        provider = (settings.ai_tts_provider or "").strip().lower()
        if provider not in _SPEAKABLE_CLOUD_PROVIDERS:
            mode, reason = (
                "local_tts",
                f"{provider or 'That provider'} cannot speak replies, only export audio.",
            )
        elif not cloud_voice_available:
            mode, reason = (
                "local_tts",
                "The AI voice needs an API key for that provider.",
            )
    if mode == "local_tts" and not local_tts_available:
        mode = "announce"
        reason = reason or "No read-aloud voice is available."

    if mode == "text":
        return VoiceReplyPlan(mode="text", fallback_reason=reason)
    if mode in ("local_tts", "ai_voice"):
        # The whole reply, never truncated: cutting speech mid-sentence is worse
        # than not speaking at all.
        return VoiceReplyPlan(mode=mode, spoken_text=compact, fallback_reason=reason)

    limit = settings.ai_voice_reply_announce_limit
    return VoiceReplyPlan(
        mode="announce",
        announce_text=f"{announce_prefix}: {truncate_announcement(compact, limit)}",
        fallback_reason=reason,
    )
