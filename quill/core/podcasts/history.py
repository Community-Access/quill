"""Recently played podcast episodes, persisted as atomic JSON.

Backs the Episode menu's Recently Played submenu and the standalone app's
optional resume-on-launch behavior. Deliberately distinct from Continue
Listening (Phase 4's virtual view of in-progress episodes): this is a
straightforward "what did I recently play" log -- most recent first,
capped, de-duplicated by (show_id, episode_guid). Mirrors
``quill/core/radio/history.py``. wx-free, strict-typed.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from quill.core.podcasts import transcript_export
from quill.core.podcasts.onboarding import OnboardingState

_FILE_NAME = "podcast_history.json"
_MAX_ENTRIES = 15


@dataclass(slots=True)
class PlayedEpisode:
    show_id: str
    episode_guid: str
    show_title: str
    episode_title: str

    def to_dict(self) -> dict[str, str]:
        return {
            "show_id": self.show_id,
            "episode_guid": self.episode_guid,
            "show_title": self.show_title,
            "episode_title": self.episode_title,
        }

    @staticmethod
    def from_dict(data: object) -> PlayedEpisode | None:
        if not isinstance(data, dict):
            return None
        show_id = str(data.get("show_id", ""))
        episode_guid = str(data.get("episode_guid", ""))
        if not show_id or not episode_guid:
            return None
        return PlayedEpisode(
            show_id=show_id,
            episode_guid=episode_guid,
            show_title=str(data.get("show_title", "")),
            episode_title=str(data.get("episode_title", "")),
        )


@dataclass(slots=True)
class PodcastHistory:
    """Recently played episodes plus the resume-on-launch preference."""

    episodes: list[PlayedEpisode] = field(default_factory=list)
    resume_on_launch: bool = False
    #: What the listener has already been shown of the first-run flow and the
    #: one-shot tips. A nested record rather than three flat fields, because it
    #: is one feature and reading it as one is how the caller uses it -- the
    #: same shape Quill Radio's history carries.
    onboarding: OnboardingState = field(default_factory=OnboardingState)
    #: Silently check GitHub releases for a newer QUILL Cast on launch (the
    #: same check Help > Check for Updates runs, just quiet unless a genuine
    #: update is found); on by default, one checkbox in Preferences (Ctrl+,)
    #: turns it off.
    check_updates_on_startup: bool = True
    #: ISO timestamp of the last update check (manual or automatic), so the
    #: startup check only hits the network once a day, not on every launch.
    last_update_check: str = ""
    #: Speak "Entered/Exited X dialog" around every modal dialog. Off by
    #: default, matching QUILL's own Settings.announce_dialog_transitions --
    #: the standalone apps previously never wired this policy at all, so
    #: dialog_contract.show_modal_dialog's "no policy set" fallback always
    #: spoke it, unlike full QUILL where it is opt-in.
    announce_dialog_transitions: bool = False
    #: How much scaffolding an exported transcript keeps: speakers, timestamps,
    #: both, or just the words. Per install, and named the same in both apps
    #: (the same shape announce_dialog_transitions has) so a transcript saved
    #: from Quill Radio and one saved from QUILL Cast come out alike.
    #: See quill.core.podcasts.transcript_export.
    transcript_detail: str = "speakers"
    #: Alt+F4 sends QUILL Cast to the system tray (still playing) instead
    #: of closing the window. Off by default; mirrors Quill Radio's
    #: RadioHistory.alt_f4_to_tray.
    alt_f4_to_tray: bool = False
    #: Winamp classic-skin transport letters (Z X C V B, arrows to seek, J,
    #: T, L) in the library and episode lists. On by default -- every letter
    #: the map claims is otherwise unused on those surfaces, and the muscle
    #: memory is real for anyone who came through Winamp. Mirrors Quill
    #: Radio's RadioHistory.winamp_playback_keys, and shares its key map.
    winamp_playback_keys: bool = True
    #: Look for new episodes on a timer. Named exactly as
    #: :class:`quill.core.settings.Settings` names them, because
    #: ``PodcastCheckMonitor`` reads its settings object duck-typed: inside
    #: QUILL that object is ``Settings``, and standalone QUILL Cast has no
    #: ``Settings`` at all -- which is why the background check silently never
    #: ran there until this record started answering for it. Same names, one
    #: monitor, one meaning.
    #:
    #: Off by default, and separate from Quill Radio's own cadence on purpose:
    #: one shared switch would mean enabling the check here enabled it there
    #: too, with no way to say "let Radio do it". What the two apps *do* share
    #: is the record of when a check happened, so they never ask one publisher
    #: twice (``PodcastLibrary.last_auto_check``).
    podcast_check_enabled: bool = False
    #: Minutes between checks; 0 is "manually only", an answer rather than the
    #: absence of one. Normalised through
    #: :mod:`quill.core.podcasts.refresh_policy`, which is the same list and
    #: the same clamping Quill Radio uses.
    podcast_check_interval_minutes: int = 60
    #: An earcon each time a check runs, so an ambient thing can be heard to
    #: be alive. Off by default: a sound four times an hour is a sound.
    podcast_check_audible_tick: bool = False
    #: Let what a check found cut across whatever is being spoken. Off by
    #: default -- new episodes are news, not an emergency.
    podcast_check_interrupt_speech: bool = False

    def record(
        self, show_id: str, episode_guid: str, *, show_title: str, episode_title: str
    ) -> None:
        """Note that this episode just started playing; it moves to the front."""
        self.episodes = [
            e for e in self.episodes if (e.show_id, e.episode_guid) != (show_id, episode_guid)
        ]
        self.episodes.insert(
            0,
            PlayedEpisode(
                show_id=show_id,
                episode_guid=episode_guid,
                show_title=show_title,
                episode_title=episode_title,
            ),
        )
        del self.episodes[_MAX_ENTRIES:]

    @property
    def last_played(self) -> PlayedEpisode | None:
        return self.episodes[0] if self.episodes else None


def _coerce_check_interval(value: object) -> int:
    """A stored cadence, through the one shared normalisation (60 if absent).

    Missing is *not* zero: an older file predates the setting, and reading it
    as "manually only" would be inventing a choice nobody made. Zero written
    down is a choice, and survives.
    """
    if value is None:
        return 60
    from quill.core.podcasts.refresh_policy import normalize_interval

    return normalize_interval(value)


def _store_path(data_dir: Path) -> Path:
    return data_dir / _FILE_NAME


def load_history(data_dir: Path) -> PodcastHistory:
    """Read history (an absent or broken file reads as empty)."""
    try:
        raw = json.loads(_store_path(data_dir).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return PodcastHistory()
    history = PodcastHistory()
    if isinstance(raw, dict):
        history.resume_on_launch = bool(raw.get("resume_on_launch", False))
        history.check_updates_on_startup = bool(raw.get("check_updates_on_startup", True))
        history.last_update_check = str(raw.get("last_update_check", ""))
        history.announce_dialog_transitions = bool(raw.get("announce_dialog_transitions", False))
        history.transcript_detail = transcript_export.normalize_detail(raw.get("transcript_detail"))
        history.alt_f4_to_tray = bool(raw.get("alt_f4_to_tray", False))
        history.winamp_playback_keys = bool(raw.get("winamp_playback_keys", True))
        history.podcast_check_enabled = bool(raw.get("podcast_check_enabled", False))
        history.podcast_check_interval_minutes = _coerce_check_interval(
            raw.get("podcast_check_interval_minutes")
        )
        history.podcast_check_audible_tick = bool(raw.get("podcast_check_audible_tick", False))
        history.podcast_check_interrupt_speech = bool(
            raw.get("podcast_check_interrupt_speech", False)
        )
        history.onboarding = OnboardingState.from_dict(raw.get("onboarding"))
        entries = raw.get("episodes")
        for entry in entries if isinstance(entries, list) else []:
            played = PlayedEpisode.from_dict(entry)
            if played is not None:
                history.episodes.append(played)
        del history.episodes[_MAX_ENTRIES:]
    return history


def save_history(data_dir: Path, history: PodcastHistory) -> None:
    """Persist history atomically."""
    from quill.core.storage import write_json_atomic

    write_json_atomic(
        _store_path(data_dir),
        {
            "resume_on_launch": history.resume_on_launch,
            "check_updates_on_startup": history.check_updates_on_startup,
            "last_update_check": history.last_update_check,
            "announce_dialog_transitions": history.announce_dialog_transitions,
            "alt_f4_to_tray": history.alt_f4_to_tray,
            "winamp_playback_keys": history.winamp_playback_keys,
            "podcast_check_enabled": history.podcast_check_enabled,
            "podcast_check_interval_minutes": history.podcast_check_interval_minutes,
            "podcast_check_audible_tick": history.podcast_check_audible_tick,
            "podcast_check_interrupt_speech": history.podcast_check_interrupt_speech,
            "onboarding": history.onboarding.to_dict(),
            "episodes": [e.to_dict() for e in history.episodes],
        },
    )
