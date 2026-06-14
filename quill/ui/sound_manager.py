"""QSP sound notification manager for QUILL's UI layer.

Owns the :class:`~quill.platform.sound_player.SoundPlayer` singleton and
exposes :func:`post_sound` as a simple, thread-safe call site that any module
can use without importing wx or caring about the audio backend.

Lifecycle (called by MainFrame)
--------------------------------
1. ``init(settings)``            — load pack and configure player at startup.
2. ``on_settings_changed(settings)`` — reload if pack path or enabled flag changed.
3. ``load_indent_tone_pack(scale)``  — overlay indent tone WAVs over the primary pack.
4. ``shutdown()``                — drain and close the player at app exit.

Partial pack / overlay design
------------------------------
The sound system supports TWO layers:

* **Primary earcon pack** — the user's chosen QSP (default: bundled Ink pack).
  Provides earcons for editing, navigation, AI, etc.
* **Indent tone overlay** — one of four built-in partial packs
  (indent_pentatonic / indent_whole_tone / indent_diatonic / indent_chromatic).
  Provides ``indent_level_N_up`` and ``indent_level_N_down`` events.
  Loaded on top of the earcon pack; absent by default.

Because packs can be partial (they may define only a subset of known events),
the Sound Events dialog reads :func:`get_loaded_events` to show only toggles
for events that actually have a sound file in the loaded pack(s).

Usage from any module
----------------------
::

    from quill.core.sound_events import SoundEvent
    from quill.ui.sound_manager import post_sound

    post_sound(SoundEvent.ABBREVIATION_EXPANDED)
    post_sound("indent_level_3_up")  # fires only when indent tone pack loaded

``post_sound`` is a no-op when the manager is not yet initialised (e.g. in
headless tests or before ``init()`` is called).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from quill.core.settings import Settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level singleton — set by init(), cleared by shutdown()
# ---------------------------------------------------------------------------

_manager: _SoundManager | None = None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def init(settings: Settings) -> None:
    """Create (or replace) the manager and load the configured pack."""
    global _manager
    if _manager is not None:
        _manager.shutdown()
    _manager = _SoundManager(settings)


def shutdown() -> None:
    """Drain and destroy the manager."""
    global _manager
    if _manager is not None:
        _manager.shutdown()
        _manager = None


def on_settings_changed(settings: Settings) -> None:
    """Reload the pack / reconfigure if relevant settings changed."""
    if _manager is not None:
        _manager.apply_settings(settings)


def post_sound(event_id: str) -> None:
    """Post an earcon for *event_id*.  Returns immediately; never raises.

    Safe to call from any thread and before :func:`init` is called.
    """
    if _manager is not None:
        _manager.play(event_id)


def toggle_mute() -> bool:
    """Flip the mute state.  Returns the new state (True == muted)."""
    if _manager is not None:
        return _manager.player.toggle_mute()
    return False


def is_active() -> bool:
    """Return True when the manager is initialised and sound is enabled."""
    return _manager is not None and _manager.enabled


def get_loaded_events() -> frozenset[str]:
    """Return the set of event IDs currently loaded across all active packs.

    Used by :class:`~quill.ui.sound_events_dialog.SoundEventsDialog` to show
    only toggles for sounds that actually exist in the loaded pack(s). Returns
    an empty frozenset when no manager is initialised.
    """
    if _manager is not None:
        return _manager.get_loaded_events()
    return frozenset()


def load_indent_tone_pack(scale: str) -> None:
    """Overlay the bundled indent tone pack for *scale* over the primary pack.

    *scale* must be one of ``"pentatonic"``, ``"whole_tone"``, ``"diatonic"``,
    ``"chromatic"``. Silently does nothing if the manager is not yet initialised
    or the requested pack is not found.
    """
    if _manager is not None:
        _manager.load_indent_tone_pack(scale)


def register_quillin_sounds(
    quillin_id: str,
    directory: Path,
    sound_pack: str,
    sound_events: tuple[tuple[str, str], ...],
) -> None:
    """Merge a Quillin's QSP contribution into the active pack.

    Called once per Quillin at registration time.  A missing or broken
    sound_pack directory is silently ignored so Quillin load never fails on
    audio issues.
    """
    if _manager is None or not sound_pack:
        return
    _manager.register_quillin_sounds(quillin_id, directory, sound_pack, sound_events)


# ---------------------------------------------------------------------------
# Internal manager class
# ---------------------------------------------------------------------------


class _SoundManager:
    def __init__(self, settings: Settings) -> None:
        from quill.platform.sound_player import SoundPlayer

        self.player = SoundPlayer()
        self.enabled: bool = False
        self._pack_path: str = ""
        self._indent_scale: str = ""
        # Tracks event IDs contributed by the indent tone overlay so they can
        # be included in get_loaded_events() without re-reading disk.
        self._indent_event_ids: frozenset[str] = frozenset()
        self.apply_settings(settings)

    def apply_settings(self, settings: Settings) -> None:
        self.enabled = bool(getattr(settings, "sound_enabled", True))
        new_pack_path = str(getattr(settings, "sound_pack_path", ""))
        volume = int(getattr(settings, "sound_volume", 80))
        events_disabled_raw = str(getattr(settings, "sound_events_disabled", ""))
        disabled = frozenset(e.strip() for e in events_disabled_raw.split(",") if e.strip())
        new_indent_scale = str(getattr(settings, "indent_tone_scale", ""))

        if not self.enabled:
            self.player.set_muted(True)
            return

        self.player.set_muted(False)

        # Reload pack only when the path actually changed.
        if new_pack_path != self._pack_path:
            self._pack_path = new_pack_path
            self._load_pack(new_pack_path, disabled)
            # Re-apply indent overlay after primary pack reload.
            if new_indent_scale:
                self.load_indent_tone_pack(new_indent_scale)
        else:
            self.player.set_disabled(disabled)

        # Switch the indent tone overlay when the chosen scale changes (including
        # turning it off, which clears the overlay).
        if new_indent_scale != self._indent_scale:
            self.load_indent_tone_pack(new_indent_scale)

        self._apply_volume(volume)

    def play(self, event_id: str) -> None:
        if self.enabled:
            self.player.play(event_id)

    def shutdown(self) -> None:
        self.player.shutdown()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _load_pack(self, pack_path: str, disabled: frozenset[str]) -> None:
        from quill.core.sound_pack import SoundPack, SoundPackError, load_sound_pack

        path = Path(pack_path) if pack_path else self._bundled_ink_path()
        if path is None:
            logger.debug("SoundManager: no pack path and no bundled pack; earcons silent")
            self.player.load_pack(SoundPack(name="(none)", author="", description="", license=""))
            return
        try:
            pack = load_sound_pack(path)
            self.player.load_pack(pack, disabled=disabled)
        except SoundPackError as exc:
            logger.warning("SoundManager: failed to load pack %s: %s", path, exc)
            self.player.load_pack(SoundPack(name="(error)", author="", description="", license=""))

    def _apply_volume(self, volume: int) -> None:
        # sound_lib backend exposes Output.set_volume(float 0.0-1.0).
        # Access it through the backend if available.
        backend = self.player._backend  # type: ignore[attr-defined]
        output = getattr(backend, "_output", None)
        if output is not None:
            try:
                output.set_volume(volume / 100.0)
            except Exception:  # noqa: BLE001
                pass

    def register_quillin_sounds(
        self,
        quillin_id: str,
        directory: Path,
        sound_pack: str,
        sound_events: tuple[tuple[str, str], ...],
    ) -> None:
        """Merge WAV bytes from a Quillin's sound_pack into the active player pack."""
        from quill.core.sound_pack import _path_is_unsafe

        # A Quillin is sandboxed: every path it supplies must stay inside its own
        # bundle. Reject traversal/absolute segments before touching the disk so a
        # malicious manifest cannot point register_event() at a file outside the
        # extension directory. (The .qsp loader already guards this; the Quillin
        # API builds paths by hand, so it must guard too.)
        bundle_root = directory.resolve()
        if _path_is_unsafe(sound_pack):
            logger.debug(
                "SoundManager: Quillin %s sound_pack path rejected (unsafe): %s",
                quillin_id,
                sound_pack,
            )
            return
        pack_dir = (directory / sound_pack).resolve()
        if not pack_dir.is_dir() or bundle_root not in (pack_dir, *pack_dir.parents):
            logger.debug(
                "SoundManager: Quillin %s sound_pack dir not found: %s", quillin_id, pack_dir
            )
            return
        for event_id, wav_name in sound_events:
            if _path_is_unsafe(wav_name):
                logger.debug(
                    "SoundManager: Quillin %s WAV name rejected (unsafe): %s",
                    quillin_id,
                    wav_name,
                )
                continue
            wav_path = (pack_dir / wav_name).resolve()
            if bundle_root not in (wav_path, *wav_path.parents):
                continue
            if not wav_path.is_file():
                continue
            try:
                wav_bytes = wav_path.read_bytes()
                self.player.register_event(event_id, wav_bytes)
            except Exception as exc:  # noqa: BLE001
                logger.debug("SoundManager: Quillin %s sound %s: %s", quillin_id, wav_name, exc)

    def get_loaded_events(self) -> frozenset[str]:
        """Return all event IDs present in the player (primary + overlay packs)."""
        primary = frozenset(self.player.loaded_event_ids())
        return primary | self._indent_event_ids

    def load_indent_tone_pack(self, scale: str) -> None:
        """Overlay the bundled indent tone pack for *scale* onto the player.

        Registers each WAV in the pack as an individual event so the primary
        pack's earcons are preserved. The old overlay events are not explicitly
        removed — they are replaced if the same event IDs exist in the new pack.
        Call again with a different scale to switch; call with ``""`` to clear.
        """
        from quill.core.sound_pack import SoundPackError, load_sound_pack

        self._indent_scale = scale
        if not scale:
            self._indent_event_ids = frozenset()
            return

        pack_path = self._bundled_indent_path(scale)
        if pack_path is None:
            logger.debug("SoundManager: indent tone pack not found for scale %r", scale)
            self._indent_event_ids = frozenset()
            return
        try:
            pack = load_sound_pack(pack_path)
        except SoundPackError as exc:
            logger.warning("SoundManager: failed to load indent pack %s: %s", pack_path, exc)
            self._indent_event_ids = frozenset()
            return

        self._indent_event_ids = frozenset(pack.events.keys())
        for event_id, wav_bytes in pack.events.items():
            self.player.register_event(event_id, wav_bytes)
        logger.debug(
            "SoundManager: indent tone overlay loaded (%s, %d events)",
            scale,
            len(pack.events),
        )

    @staticmethod
    def _bundled_ink_path() -> Path | None:
        """Return the path to the bundled Ink pack, or None if not present."""
        try:
            import quill

            ink = Path(quill.__file__).parent / "assets" / "sound_packs" / "ink"
            return ink if ink.exists() else None
        except Exception:  # noqa: BLE001
            return None

    @staticmethod
    def _bundled_indent_path(scale: str) -> Path | None:
        """Return the path to the bundled indent tone pack for *scale*."""
        valid = {"pentatonic", "whole_tone", "diatonic", "chromatic"}
        if scale not in valid:
            return None
        try:
            import quill

            pack = Path(quill.__file__).parent / "assets" / "sound_packs" / f"indent_{scale}"
            return pack if pack.exists() else None
        except Exception:  # noqa: BLE001
            return None
