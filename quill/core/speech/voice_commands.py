"""Offline voice commands (#663, Speech S5).

Map a short *spoken phrase* — captured and transcribed entirely on-device by the
existing ``quill/core/speech`` stack — onto a QUILL command, and dispatch it.
The set of commands voice can invoke is the **agent safe-tool allowlist**
(:data:`quill.core.ai.agent.SAFE_TOOL_IDS`): voice never reaches anything outside
that curated, non-destructive set, so "saying the wrong thing" can't run a
dangerous action.

This module is pure and wx-free: it builds the voice-command catalog from the
command registry, matches a transcript to a command, and decides whether voice
commands are even allowed (off by default, and always off in Safe Mode). The UI
layer owns microphone capture, transcription, and the actual ``registry.run``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from quill.core.ai.agent import SAFE_TOOL_IDS

__all__ = [
    "VoiceCommand",
    "VoiceMatch",
    "VoiceOutcome",
    "CANCEL_PHRASES",
    "WAKE_PHRASES",
    "normalize",
    "build_voice_commands",
    "extract_transcript_body",
    "match_command",
    "resolve_transcript",
    "voice_commands_available",
]

# Extra spoken aliases beyond each command's registry title. Keyed by command id;
# every id here is also in SAFE_TOOL_IDS (a test asserts the converse direction).
_ALIASES: dict[str, tuple[str, ...]] = {
    "file.save": ("save", "save file", "save document"),
    "file.save_all": ("save all", "save everything"),
    "file.new": ("new", "new document", "new file"),
    "edit.undo": ("undo",),
    "edit.redo": ("redo",),
    "edit.select_all": ("select all",),
    "format.bold": ("bold", "make bold"),
    "format.italic": ("italic", "make italic"),
    "format.upper_case": ("uppercase", "upper case", "make uppercase"),
    "format.lower_case": ("lowercase", "lower case", "make lowercase"),
    "format.title_case": ("title case",),
    "format.sentence_case": ("sentence case",),
    "format.insert_bullet_list": ("bullet list", "insert bullet list", "bulleted list"),
    "format.insert_numbered_list": ("numbered list", "insert numbered list"),
    "tools.word_count": ("word count", "count words"),
    "tools.spell_check_dialog": ("spell check", "check spelling"),
    "tools.read_aloud_start_pause": ("read aloud", "start reading", "pause reading"),
    "tools.read_aloud_stop": ("stop reading", "stop read aloud"),
    "navigate.next_heading": ("next heading",),
    "navigate.previous_heading": ("previous heading", "prior heading"),
    "navigate.outline_navigator": ("outline", "outline navigator", "show outline"),
    "edit.find": ("find", "search", "find text"),
    "view.toggle_soft_wrap": ("soft wrap", "toggle soft wrap", "word wrap"),
    "app.command_palette": ("command palette", "commands", "show commands"),
}

#: Phrases that cancel the listening session instead of running a command.
CANCEL_PHRASES = frozenset({"cancel", "never mind", "nevermind", "stop", "dismiss"})

_WORD_RE = re.compile(r"[a-z0-9]+")
#: A token-overlap match must reach this fraction of the phrase's words.
_MATCH_THRESHOLD = 0.6


@dataclass(frozen=True, slots=True)
class VoiceCommand:
    """A command voice can invoke, with the spoken phrases that select it."""

    command_id: str
    title: str
    phrases: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class VoiceMatch:
    """A resolved phrase->command match and its confidence in ``[0, 1]``."""

    command_id: str
    title: str
    score: float


@dataclass(frozen=True, slots=True)
class VoiceOutcome:
    """The result of resolving one transcript."""

    kind: str  # "run" | "cancel" | "no_match" | "disabled"
    message: str
    command_id: str | None = None


def normalize(text: str) -> str:
    """Lowercase ``text`` and collapse it to space-separated word tokens."""
    return " ".join(_WORD_RE.findall(text.lower()))


def _phrases_for(command_id: str, title: str) -> tuple[str, ...]:
    phrases = set(_ALIASES.get(command_id, ()))
    normalized_title = normalize(title)
    if normalized_title:
        phrases.add(normalized_title)
    return tuple(sorted(normalize(p) for p in phrases if normalize(p)))


def build_voice_commands(
    registry: object, *, allowlist: tuple[str, ...] = SAFE_TOOL_IDS
) -> tuple[VoiceCommand, ...]:
    """Build the voice-invokable catalog from ``registry``, limited to ``allowlist``.

    Only commands that are both in the allowlist *and* registered (so they have a
    real handler) are included.
    """
    get = getattr(registry, "get", None)
    commands: list[VoiceCommand] = []
    for command_id in allowlist:
        command = get(command_id) if callable(get) else None
        if command is None:
            continue
        title = getattr(command, "title", command_id)
        commands.append(VoiceCommand(command_id, title, _phrases_for(command_id, title)))
    return tuple(commands)


def match_command(transcript: str, commands: tuple[VoiceCommand, ...]) -> VoiceMatch | None:
    """Return the best command match for ``transcript``, or ``None`` below threshold.

    Exact phrase equality scores 1.0; a phrase appearing as a whole sub-sequence
    of the transcript scores 0.9; otherwise the score is the fraction of the
    phrase's words present in the transcript, accepted at or above
    :data:`_MATCH_THRESHOLD`.
    """
    spoken = normalize(transcript)
    if not spoken:
        return None
    spoken_tokens = spoken.split()
    best: VoiceMatch | None = None
    for command in commands:
        for phrase in command.phrases:
            score = _phrase_score(phrase, spoken, spoken_tokens)
            if score > 0 and (best is None or score > best.score):
                best = VoiceMatch(command.command_id, command.title, score)
    if best is None or best.score < _MATCH_THRESHOLD:
        return None
    return best


def _phrase_score(phrase: str, spoken: str, spoken_tokens: list[str]) -> float:
    if not phrase:
        return 0.0
    if phrase == spoken:
        return 1.0
    phrase_tokens = phrase.split()
    if _contains_subsequence(spoken_tokens, phrase_tokens):
        return 0.9
    present = sum(1 for token in phrase_tokens if token in spoken_tokens)
    return present / len(phrase_tokens)


def _contains_subsequence(haystack: list[str], needle: list[str]) -> bool:
    if not needle or len(needle) > len(haystack):
        return False
    for start in range(len(haystack) - len(needle) + 1):
        if haystack[start : start + len(needle)] == needle:
            return True
    return False


def resolve_transcript(
    transcript: str, registry: object, *, allowlist: tuple[str, ...] = SAFE_TOOL_IDS
) -> VoiceOutcome:
    """Resolve a transcript to a :class:`VoiceOutcome` (run / cancel / no match)."""
    spoken = normalize(transcript)
    if spoken in CANCEL_PHRASES:
        return VoiceOutcome("cancel", "Voice command cancelled.")
    commands = build_voice_commands(registry, allowlist=allowlist)
    match = match_command(transcript, commands)
    if match is None:
        heard = transcript.strip() or "nothing"
        return VoiceOutcome("no_match", f"No command matched. Heard: {heard}.")
    return VoiceOutcome("run", f"Running {match.title}.", command_id=match.command_id)


def voice_commands_available(settings: object, *, safe_mode_active: bool) -> bool:
    """True only when the user enabled voice commands and Safe Mode is off.

    Voice commands are off by default (``settings.voice_commands_enabled``) and
    are always disabled in Safe Mode, matching the assistant/agent guarantees.
    """
    if safe_mode_active:
        return False
    return bool(getattr(settings, "voice_commands_enabled", False))


# --- wake phrase (Hey QUILL Phase 3 groundwork) ------------------------------
#
# Kept from the retired Windows-dictation-era module: the one piece the
# always-listening wake word will need. Not used by the push-to-talk flow.

WAKE_PHRASES: tuple[str, ...] = ("hey quill", "quill")


def extract_transcript_body(transcript: str) -> str | None:
    """Strip a wake phrase from ``transcript``; ``None`` if no wake phrase leads.

    Returns ``""`` for a wake-only utterance ("hey quill" alone — arm and
    wait), the remaining command text when a wake phrase prefixes it, and
    ``None`` when the transcript did not address QUILL at all.
    """
    spoken = normalize(transcript)
    for wake_phrase in WAKE_PHRASES:
        if spoken == wake_phrase:
            return ""
        prefix = f"{wake_phrase} "
        if spoken.startswith(prefix):
            return spoken[len(prefix) :].strip()
    return None
