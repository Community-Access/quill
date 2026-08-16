"""Tools > Media > Internet Radio -- menu, commands, hotkeys, status bar
mini-player, and the system tray radio section.

RadioBrowser search, the bundled ACB Media category, custom stations, and
the website link finder all funnel through the one shared
``RadioPlayerController`` created here, so playback survives closing any of
the dialogs. See PRD §5.84f for the feature plan and
``quill/ui/radio/player_controller.py`` for why this always uses the
wx.media backend.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from quill.core.audio.exact_optilab import ExactOptilab
from quill.core.paths import app_data_dir
from quill.core.radio import favorites as radio_favorites
from quill.core.radio import history as radio_history
from quill.core.radio import radio_browser, wake_timer
from quill.core.radio.favorites import FavoriteStation
from quill.core.radio.models import RadioStation
from quill.core.radio.recording import (
    RadioRecorder,
    RecordingError,
    load_recording_settings,
    save_recording_settings,
)
from quill.core.radio.recording_join import describe_reconnect
from quill.core.radio.recording_schedule import RecordingScheduler
from quill.core.sound_events import SoundEvent
from quill.core.speech.ffmpeg import ffmpeg_available
from quill.ui.radio import quick_play
from quill.ui.radio.add_station_dialog import AddStationDialog
from quill.ui.radio.link_finder_dialog import LinkFinderDialog
from quill.ui.radio.player_controller import (
    RadioPlaybackState,
    RadioPlayerController,
    ResolvedEnhancement,
)
from quill.ui.radio.recording_settings_dialog import RecordingSettingsDialog
from quill.ui.radio.schedule_recording_dialog import ScheduleRecordingDialog
from quill.ui.radio.station_browser_dialog import StationBrowserDialog


def _search_catalog(host: object) -> object | None:
    """The catalog for Find Stations' instant lane, or None when off."""
    from quill.ui.radio import catalog_ui

    return catalog_ui.catalog_for(host)


_SAFE_MODE_MESSAGE = "Internet Radio is disabled in Safe Mode. Restart QUILL normally to use it."
_NO_FFMPEG_MESSAGE = (
    "Recording needs the FFmpeg optional component. Install it from "
    "Help > Download Optional Components (Audio: export, playback & chapters), "
    "then try again."
)


class RadioMixin:
    """Adds Internet Radio to ``MainFrame``."""

    # -- setup --------------------------------------------------------------

    def _init_radio(self) -> None:
        # Parents the player controller on self.frame: MainFrame.__init__ must
        # only call this (and _init_podcasts) after the frame is constructed,
        # or startup dies with AttributeError('frame').
        self._radio_favorites = radio_favorites.load_favorites(app_data_dir())
        self._radio_history = radio_history.load_history(app_data_dir())
        # Apply the persisted verbose-logging preference (quill-radio #5).
        from quill.core.radio.radio_logging import set_radio_debug

        set_radio_debug(self._radio_history.debug_mode)
        self._radio_history_key = ""
        self._radio_track_title = ""
        self._radio_fallback_tried = ""
        self._radio_ever_played = False
        # Track-title poller: fires only while a stream plays; each tick reads
        # one ICY metadata block from the playing stream, off-thread.
        self._radio_title_timer = self._wx.Timer(self.frame)
        self.frame.Bind(
            self._wx.EVT_TIMER,
            lambda _e: self._radio_fetch_track_title(),
            self._radio_title_timer,
        )
        from quill.core.spotify.session import SpotifySession

        #: Hands the radio player a fresh Spotify access token (refreshing the
        #: stored one as needed) so a spotify: station can play on the Web
        #: Playback engine. Returns "" until the user connects Spotify.
        self._spotify_session = SpotifySession()
        self._radio_controller = RadioPlayerController(
            self.frame,
            on_state_changed=self._on_radio_state_changed,
            on_register_click=self._radio_register_click,
            before_play=self._stop_podcast_before_radio,
            on_enhance_error=self._on_radio_enhance_error,
            resolve_enhancement=self._radio_resolve_enhancement,
            resolve_volume=self._radio_resolve_volume,
            output_device=self._radio_history.output_device,
            on_output_device_error=self._on_radio_output_device_error,
            playback_engine=self._radio_history.playback_engine,
            on_buffering=lambda: self._wx.CallAfter(self._radio_announce_buffering),
            spotify_token_provider=self._spotify_session.access_token,
            resolve_youtube=self._radio_resolve_youtube,
        )
        self._radio_controller.set_enhancement(
            bass_db=self._radio_history.eq_bass_db,
            mid_db=self._radio_history.eq_mid_db,
            treble_db=self._radio_history.eq_treble_db,
            compressor_enabled=self._radio_history.compressor_enabled,
        )
        self._radio_controller.set_sound_options(
            channel_mode=self._radio_history.channel_mode,
            night_mode_enabled=self._radio_history.night_mode_enabled,
            optilab_enabled=self._radio_history.optilab_enabled,
            optilab_mode=self._radio_history.optilab_mode,
            optilab_input_db=self._radio_history.optilab_input_db,
            optilab_auto_adapt=self._radio_history.optilab_auto_adapt,
            optilab_exact_live=self._radio_history.optilab_exact_live,
        )
        self._radio_controller.set_volume_boost(self._radio_history.volume_boost)
        self._radio_recording_settings = load_recording_settings(app_data_dir())
        self._radio_recorder = RadioRecorder(
            on_state_changed=self._on_radio_recording_changed,
            on_reconnect=self._on_radio_recording_reconnect,
            # The recorder builds the sentence (it knows how many parts there
            # were and whether the join succeeded); the UI only speaks it.
            on_parts_joined=lambda note: self._wx.CallAfter(self._announce, note),
            # Same contract for the exact-OptiLab pass: the recorder knows
            # whether it ran, and says so either way -- a listener who turned it
            # on is entitled to know whether the file they kept actually got it.
            on_exact_processed=lambda note: self._wx.CallAfter(self._announce, note),
            # A recording that captured nothing is reported, in words, with the
            # reason. Saying "Recording saved" over an empty file -- or saying
            # nothing at all -- sends somebody looking in a folder for audio
            # that does not exist, which is exactly what happened.
            on_capture_failed=lambda station, reason: self._wx.CallAfter(
                self._radio_announce_capture_failed, station, reason
            ),
        )
        # The ACTIVE machinery below fires recordings, shows resume prompts, and
        # speaks missed-recording reports on its own. In a public build the
        # editor-embedded radio is gated off (core.radio, #1340) and none of it
        # may run — a user with a leftover schedule from a pre-gate build must
        # not get recordings and modal prompts from a feature with no UI. The
        # passive state above stays so shutdown and attribute access are safe.
        if not self._feature_enabled("core.radio"):
            self._radio_scheduler = None
            self._radio_wake_watcher = None
            self._radio_last_seen_timer = None
            return
        self._radio_scheduler = RecordingScheduler(
            data_dir=app_data_dir(),
            recorder=self._radio_recorder,
            recording_settings=self._radio_recording_settings,
            on_fired=self._on_radio_scheduled_recording_fired,
            on_busy=self._on_radio_scheduled_recording_busy,
            filter_graph_provider=self._radio_recording_filter_graph,
        )
        self._radio_wake_watcher = wake_timer.WakeUpWatcher(
            app_data_dir(), on_wake=self._on_radio_wake_up
        )
        # R2/11.6: announce scheduled recordings missed while QUILL was closed
        # (the embedded host previously had no missed reporting), then stamp
        # last_seen. Deferred so it never blocks the window coming up.
        self._wx.CallAfter(self._report_missed_recordings)
        # R3: reconcile temp-dir strays from a crash and offer to resume an
        # in-progress recording found via the persisted marker. Runs after the
        # missed report, deferred so the window is up first.
        self._wx.CallAfter(self._reconcile_and_offer_radio_resume)
        # R3: stamp last_seen once a minute so a crash still leaves an accurate
        # missed-recording window (the close-path stamp alone is lost on a kill).
        self._radio_last_seen_timer = self._wx.Timer(self.frame)
        self.frame.Bind(
            self._wx.EVT_TIMER,
            lambda _e: self._radio_minute_tick(),
            self._radio_last_seen_timer,
        )
        self._radio_last_seen_timer.Start(60_000)
        # Re-asked at launch: a one-shot task is spent once it fires, and the
        # schedule may have been edited in another session. Deferred so a slow
        # schtasks call cannot hold up the window coming up.
        self._wx.CallAfter(self._refresh_radio_wake_task)
        # Layer 1 of the station catalog: a startup check for updates, off the
        # UI thread, skipped when fresh (6-hour floor) or toggled off.
        from quill.ui.radio import catalog_ui as _catalog_ui

        self._wx.CallAfter(_catalog_ui.refresh_on_startup, self)

    def _radio_minute_tick(self) -> None:
        """Once a minute: stamp last_seen, and re-ask about standby.

        The sleep inhibitor is otherwise only recomputed when playback or
        recording changes state -- and "a scheduled recording is now five
        minutes away" is a change in neither, so without this tick the
        approach of a recording would never reach it.
        """
        self._stamp_radio_last_seen()
        self._update_sleep_inhibitor()
        # Layer 2 of the station catalog: the staggered background refresh
        # takes its step here when the cadence says one is due -- a trickle,
        # never a burst, and never anything in Safe Mode or when switched off.
        from quill.ui.radio import catalog_ui

        catalog_ui.maybe_refresh_on_tick(self)

    def _shutdown_radio(self) -> None:
        """Tear down every radio subsystem and stamp last_seen (R2/11.6).

        Consolidated so the embedded close path is one safe call instead of a
        per-subsystem block that grows each time radio gains a subsystem
        (GATE-11: ``main_frame.py`` must not grow). Each component is guarded so
        one failure cannot block the rest -- the same isolation the per-line
        ``_safely`` calls gave. The standalone host keeps its own close path.
        """
        for attr, _label in (
            ("_radio_controller", "radio player"),
            ("_radio_recorder", "radio recorder"),
            ("_radio_scheduler", "radio recording scheduler"),
            ("_radio_wake_watcher", "radio wake-up timer"),
        ):
            obj = getattr(self, attr, None)
            shutdown = getattr(obj, "shutdown", None)
            if callable(shutdown):
                try:
                    shutdown()
                except Exception:  # noqa: BLE001 - shutdown must never block exit
                    pass
        # R3: stop the periodic last_seen timer.
        timer = getattr(self, "_radio_last_seen_timer", None)
        if timer is not None:
            try:
                timer.Stop()
            except Exception:  # noqa: BLE001
                pass
        # R3: a clean close clears the active-recording marker so the next launch
        # does not offer a stale resume (only a crash/kill leaves it behind).
        self._clear_radio_recording_marker()
        # Stamp that QUILL Radio was running now so the next launch can report
        # scheduled recordings missed while it was closed.
        self._stamp_radio_last_seen()
        # Close the station catalog's read connection so the next refresh (or
        # a rebuild) can collect this generation's file.
        from quill.ui.radio import catalog_ui

        catalog_ui.shutdown(self)

    # -- R3: resume across restart -------------------------------------------

    def _reconcile_and_offer_radio_resume(self) -> None:
        """Move crash-orphaned temp files home, then offer to resume an
        in-progress recording found via the persisted marker (R3).

        Runs once at launch (deferred). Reconcile is always done and announced;
        resume honors the remembered choice (ask/always/never) and the grace
        window. A marker past its grace is cleared and skipped.
        """
        from quill.core.radio.recording_resume import (
            load_markers,
            reconcile_temp_strays,
            remaining_minutes,
            within_resume_grace,
        )

        # 1) Reconcile temp-dir strays from a crash (R3/12, 13.6).
        try:
            moved = reconcile_temp_strays(self._radio_recording_settings)
        except Exception:  # noqa: BLE001 - reconcile must never block launch
            moved = []
        if moved:
            self._announce(
                f"Recovered {len(moved)} recording file(s) left in the temp "
                f"folder from an earlier crash; moved to your recordings folder."
            )

        # 2) Offer to resume in-progress recordings found via the markers
        #    (concurrent recording: there may be several). Markers past their
        #    grace window are cleared and skipped; the rest are resumed per the
        #    remembered choice, or offered in one batched prompt for "ask".
        from quill.core.paths import app_data_dir

        try:
            markers = load_markers(app_data_dir())
        except Exception:  # noqa: BLE001
            markers = []
        resumable: list[tuple[object, int]] = []
        for marker in markers:
            if not getattr(marker, "stream_url", ""):
                continue
            if not within_resume_grace(marker):
                # The show is long over: clear the stale marker and move on.
                self._clear_radio_recording_marker(getattr(marker, "job_id", "") or None)
                continue
            resumable.append((marker, remaining_minutes(marker)))
        if not resumable:
            return
        choice = self._radio_history.recording_resume_choice
        if choice == "never":
            for marker, _left in resumable:
                self._clear_radio_recording_marker(getattr(marker, "job_id", "") or None)
            return
        if choice == "always":
            for marker, left in resumable:
                self._start_radio_resume(marker, left)
            return
        # "ask": one dialog for one recording, a batched prompt for several.
        self._ask_radio_resume(resumable)

    def _ask_radio_resume(self, resumable: list[tuple[object, int]]) -> None:
        from quill.ui.radio.resume_recording_dialog import (
            ResumeRecordingDialog,
            ResumeRecordingsBatchDialog,
        )

        if len(resumable) == 1:
            marker, left = resumable[0]
            station = getattr(marker, "station_name", "") or "the stream"
            end = getattr(marker, "scheduled_end", "")
            result = ResumeRecordingDialog(
                self.frame,
                station_name=station,
                remaining_minutes=left,
                scheduled_end=end,
                announce_cb=self._announce,
            ).show()
        else:
            lines = [
                f"{getattr(m, 'station_name', '') or 'Recording'} -- {left} minute(s) left"
                for m, left in resumable
            ]
            result = ResumeRecordingsBatchDialog(
                self.frame, lines=lines, announce_cb=self._announce
            ).show()
        if result is None:
            return  # dismissed/cancelled -> skip, leave markers to age out
        action, remember = result
        if remember:
            self._radio_history.recording_resume_choice = (
                "always" if action == "resume" else "never"
            )
            from quill.core.paths import app_data_dir
            from quill.core.radio import history as radio_history

            radio_history.save_history(app_data_dir(), self._radio_history)
        if action == "resume":
            for marker, left in resumable:
                self._start_radio_resume(marker, left)
        else:
            for marker, _left in resumable:
                self._clear_radio_recording_marker(getattr(marker, "job_id", "") or None)

    def _start_radio_resume(self, marker: object, left: int) -> None:
        """Resume the marker's recording for the remaining minutes (R3).

        Concurrent recording: no longer refuses when something else is already
        recording -- a resumed recording simply joins the others.
        """
        from quill.core.speech.ffmpeg import ffmpeg_available

        job_id = getattr(marker, "job_id", "") or None
        if not ffmpeg_available():
            self._announce("Cannot resume recording: FFmpeg is not installed.")
            self._clear_radio_recording_marker(job_id)
            return
        station_name = getattr(marker, "station_name", "") or "Recording"
        stream_url = getattr(marker, "stream_url", "") or ""
        entry_id = getattr(marker, "entry_id", "") or ""
        if not stream_url:
            self._clear_radio_recording_marker(job_id)
            return
        try:
            self._radio_recorder.start(
                station_name=station_name,
                stream_url=stream_url,
                settings=self._radio_recording_settings,
                duration_minutes=max(1, left),
                filter_graph=self._radio_recording_filter_graph(),
                exact_optilab=self._radio_recording_exact(),
                entry_id=entry_id,
            )
            self._announce(
                f"Resuming recording of {station_name} for {max(1, left)} minute(s).",
                sound=SoundEvent.RADIO_RECORDING_STARTED,
            )
            # The old marker (from the previous run) is superseded by the fresh
            # one the new job wrote under its own id; clear the stale one.
            self._clear_radio_recording_marker(job_id)
        except Exception as exc:  # noqa: BLE001 - a failed resume is announced, not fatal
            self._announce(f"Could not resume the recording: {exc}")
            self._clear_radio_recording_marker(job_id)

    def _stop_podcast_before_radio(self) -> None:
        """Never double-play: starting a radio stream silences a playing
        podcast episode first (position is checkpointed by its stop path).
        Works in MainFrame (both players live) and is a no-op in standalone
        Quill Radio, which has no podcast controller."""
        podcast = getattr(self, "_podcast_controller", None)
        if podcast is not None:
            podcast.stop()

    def _radio_register_click(self, station_uuid: str) -> None:
        try:
            radio_browser.register_click(station_uuid, safe_mode=self._safe_mode)
        except Exception:  # noqa: BLE001 - a missed click-vote must never surface
            pass

    def _save_radio_favorites(self) -> None:
        radio_favorites.save_favorites(app_data_dir(), self._radio_favorites)

    def _persist_radio_favorites(self) -> None:
        """Write favorites to disk WITHOUT touching any favorites UI.

        For background, non-structural updates -- a favorite's remembered
        volume changing as you hold Volume Up/Down -- where the visible
        favorites list is unchanged. The standalone app's
        ``_save_radio_favorites`` rebuilds its favorites tree, which
        transiently re-selects items and makes the screen reader re-announce
        the station on every keystroke (#1154). Structural changes (add /
        remove / rename / move / sort) still go through
        ``_save_radio_favorites`` so the tree reflects them.
        """
        radio_favorites.save_favorites(app_data_dir(), self._radio_favorites)

    # -- recording --------------------------------------------------------

    def _on_radio_recording_changed(
        self, is_recording: bool, destination: Path | None, job_id: str = ""
    ) -> None:
        self._wx.CallAfter(self._apply_radio_recording_changed, is_recording, destination, job_id)

    def _apply_radio_recording_changed(
        self, is_recording: bool, destination: Path | None, job_id: str = ""
    ) -> None:
        # A video that carries described audio says so, once. Without this the
        # feature only helps people who already know it exists -- and those are
        # the last people who need telling.
        from quill.ui.radio import track_selection

        track_selection.announce_described_if_new(self)
        self._refresh_statusbar()
        self._refresh_radio_tray_tooltip()
        self._update_sleep_inhibitor()
        if is_recording:
            # R3: persist a per-recording marker (keyed by job id) so a restart
            # can offer to resume this exact recording. Built from the recorder's
            # live state (the temp path, the final destination, the start time,
            # the duration cap) so the marker is correct even in a temp dir.
            self._persist_radio_recording_marker(job_id)
        else:
            # R3: a clean stop clears just this recording's marker -- only a
            # crash/kill leaves markers behind for the next launch to find.
            self._clear_radio_recording_marker(job_id)
            if destination is not None:
                # The recorder's own stop-and-finalize edge: the one moment a
                # capture is really over and on disk (#1302).
                self._announce(
                    f"Recording saved: {destination.name}",
                    sound=SoundEvent.RADIO_RECORDING_STOPPED,
                )

    def _radio_announce_capture_failed(self, station: str, reason: str) -> None:
        """Say that a recording captured nothing, and why.

        One sentence, on the error cue rather than the saved cue, because the
        two outcomes must never sound alike. The reason comes from the recorder
        (which read ffmpeg's own last words); this only speaks it.
        """
        self._announce(
            f"Recording of {station} saved nothing: {reason}. No file was kept.",
            sound=SoundEvent.RADIO_STREAM_ERROR,
        )
        self._refresh_statusbar()

    def _persist_radio_recording_marker(self, job_id: str = "") -> None:
        """Write a per-recording marker so a crash can offer to resume it.
        See :mod:`quill.ui.radio.recording_markers`."""
        from quill.ui.radio import recording_markers

        recording_markers.persist(self, job_id)

    def _clear_radio_recording_marker(self, job_id: str | None = None) -> None:
        """Clear one recording's marker, or all of them when *job_id* is None."""
        from quill.ui.radio import recording_markers

        recording_markers.clear(self, job_id)

    def _radio_announce_buffering(self) -> None:
        """A mid-stream rebuffer, spoken instead of dead air -- cued once per
        run of stalls (#1302). A stream that keeps dropping calls this over and
        over without ever leaving PLAYING, so the earcon is armed again only by
        a real playback state change: ten rebuffers make one sound, not ten,
        while the words still arrive each time because each stall is news.
        """
        cue = "" if getattr(self, "_radio_buffer_cued", False) else SoundEvent.RADIO_BUFFERING
        self._radio_buffer_cued = True
        self._announce("Buffering...", sound=cue)

    def _on_radio_recording_reconnect(self, attempt: int, maximum: int) -> None:
        self._wx.CallAfter(self._announce, describe_reconnect(attempt, maximum))

    def _on_radio_scheduled_recording_fired(self, entry: object, error: str) -> None:
        self._wx.CallAfter(self._apply_radio_scheduled_recording_fired, entry, error)

    def _apply_radio_scheduled_recording_fired(self, entry: object, error: str) -> None:
        station_name = getattr(entry, "station_name", "")
        if error:
            self._announce(f"Scheduled recording of {station_name} could not start: {error}")
        else:
            self._announce(
                f"Scheduled recording started: {station_name}",
                sound=SoundEvent.RADIO_RECORDING_STARTED,
            )
        self._refresh_statusbar()

    def _on_radio_scheduled_recording_busy(self, entry: object) -> None:
        """A scheduled fire was deferred because the recorder is busy (R2/11.3):
        the entry is held pending and retried within its window instead of being
        burned. Announced once per deferral so the user knows it is queued."""
        self._wx.CallAfter(
            self._announce,
            f"Scheduled recording of {getattr(entry, 'station_name', '')} is queued; "
            "it will start when the current recording finishes.",
        )

    def _stamp_radio_last_seen(self) -> None:
        """Record that QUILL Radio was running *now* (R2/11.6 + R3).

        The scheduler is in-process, so missed-recording reporting can only
        cover time QUILL was actually open. Stamping ``last_seen`` on close (and
        periodically while open) lets the next launch report exactly the window
        the app was down. Shared by embedded QUILL and standalone Quill Radio.
        """
        from datetime import datetime

        from quill.core.paths import app_data_dir
        from quill.core.radio import history as radio_history

        history = self._radio_history
        history.last_seen = datetime.now().isoformat()
        radio_history.save_history(app_data_dir(), history)

    def _report_missed_recordings(self) -> None:
        """Announce scheduled recordings whose time passed while closed (#4).

        Shared by embedded QUILL and standalone Quill Radio (R2/11.6: previously
        only the standalone app reported missed recordings). Compares the
        schedule against the window the app was down (``last_seen`` -> now) and
        speaks a one-line summary; occurrences whose window is still open at
        launch are excluded (R2/11.7) -- the scheduler will start those late.
        """
        from datetime import datetime

        from quill.core.radio.recording_schedule import describe_missed, missed_occurrences

        history = self._radio_history
        now = datetime.now()
        since = now
        if history.last_seen:
            try:
                since = datetime.fromisoformat(history.last_seen)
            except ValueError:
                since = now
        message = describe_missed(
            missed_occurrences(self._radio_scheduler.entries, since=since, now=now)
        )
        if message:
            self._announce(message)
        # Stamp that we were running now (R2/11.6): the next launch reports
        # only the window the app was actually down.
        self._stamp_radio_last_seen()

    def _radio_no_ffmpeg_message(self) -> str:
        """Where to get ffmpeg, phrased for the hosting app: QUILL points at
        its components hub; the standalone apps override this to point at
        their own Help > Get FFmpeg... item."""
        return _NO_FFMPEG_MESSAGE

    def _radio_playing_job_id(self) -> str:
        """The job id of the active recording whose stream is the station now
        playing, or "" (concurrent recording).

        Record Now and its menu label act on the station you are *listening* to:
        if that station is being recorded this returns its job id (so Record Now
        stops it), otherwise Record Now starts a new concurrent recording. Any
        other recording is stopped from the Recordings list.
        """
        controller = getattr(self, "_radio_controller", None)
        station = controller.state.station if controller is not None else None
        if station is None:
            return ""
        recorder = getattr(self, "_radio_recorder", None)
        jobs = getattr(recorder, "active_jobs", None)
        if not callable(jobs):
            return ""
        for job in jobs():
            if getattr(job, "stream_url", "") == station.stream_url:
                return getattr(job, "job_id", "") or ""
        return ""

    def radio_record_toggle(self) -> None:
        if not ffmpeg_available():
            self._show_message_box(
                self._radio_no_ffmpeg_message(),
                "Internet Radio",
                self._wx.ICON_INFORMATION | self._wx.OK,
            )
            return
        # Concurrent recording: if the station you are listening to is already
        # recording, stop that one; otherwise start a new recording of it. A
        # second, different station keeps recording in the background.
        playing_job = self._radio_playing_job_id()
        if playing_job:
            self._radio_recorder.stop(playing_job)
            self._announce("Stopping recording...")
            return
        controller = getattr(self, "_radio_controller", None)
        station = controller.state.station if controller is not None else None
        if station is None:
            self._announce("Nothing is playing to record. Start a station first.")
            return
        try:
            self._radio_recorder.start(
                station_name=station.name,
                stream_url=station.stream_url,
                settings=self._radio_recording_settings,
                filter_graph=self._radio_recording_filter_graph(),
                exact_optilab=self._radio_recording_exact(),
            )
        except RecordingError as error:
            self._announce(str(error))
            return
        # "Recording started" (not the label-like "Recording X") so it is
        # unmistakable that pressing the command actually began a capture.
        self._announce(
            f"Recording started: {station.name}.", sound=SoundEvent.RADIO_RECORDING_STARTED
        )
        self._refresh_statusbar()

    def radio_stop_all_recordings(self) -> None:
        """Stop every recording at once (concurrent recording). Announces how
        many were stopped, or that nothing was recording."""
        recorder = getattr(self, "_radio_recorder", None)
        count = int(getattr(recorder, "active_count", 0) or 0)
        if count < 1:
            self._announce("Nothing is recording right now.")
            return
        stop_all = getattr(recorder, "stop_all", None)
        if callable(stop_all):
            stop_all()
        else:
            recorder.stop()
        noun = "recording" if count == 1 else "recordings"
        self._announce(f"Stopping all {count} {noun}...")
        self._refresh_statusbar()

    def _radio_recording_filter_graph(self) -> str:
        """The current Sound Enhancements filter graph, or "" if Recording
        Settings' "Apply Sound Enhancements to recordings" is off.

        When the recording will afterwards go through the *real* OptiLab engine
        (:meth:`_radio_recording_exact`), the OptiLab filters are left out here:
        the engine is doing that work, and a recording processed by both the
        adaptation and the original would be neither. Everything else -- EQ,
        compressor, channel mode, night mode -- still applies during capture."""
        if not self._radio_recording_settings.apply_sound_enhancements:
            return ""
        from quill.core.audio_enhance import build_filter_graph

        history = self._radio_history
        exact = self._radio_recording_exact()
        return build_filter_graph(
            history.eq_bass_db,
            history.eq_mid_db,
            history.eq_treble_db,
            compressor_enabled=history.compressor_enabled,
            channel_mode=history.channel_mode,
            night_mode_enabled=history.night_mode_enabled,
            optilab_enabled=history.optilab_enabled and exact is None,
            optilab_mode="off" if exact is not None else history.optilab_mode,
            optilab_input_db=history.optilab_input_db,
            optilab_auto_adapt=history.optilab_auto_adapt,
        )

    def _radio_recording_exact(self) -> ExactOptilab | None:
        """The exact-OptiLab pass a new recording should get, or None.

        None unless the listener asked for it, has broadcast polish on with a
        real mode, and this build actually includes the OptiLab component --
        every one of which is a reason the recording simply comes out as it does
        today, not a reason to fail."""
        from quill.core.audio import exact_optilab

        history = self._radio_history
        if not history.optilab_exact or not history.optilab_enabled:
            return None
        if history.optilab_mode not in ("podcast", "stream", "limiter"):
            return None
        if not exact_optilab.available():
            return None
        return ExactOptilab(
            mode=history.optilab_mode,
            input_db=history.optilab_input_db,
            auto_adapt=history.optilab_auto_adapt,
        )

    def _radio_open_recording_settings(self) -> None:
        dialog = RecordingSettingsDialog(
            self.frame, settings=self._radio_recording_settings, announce_cb=self._announce
        )
        updated = dialog.show()
        if updated is None:
            return
        self._radio_recording_settings = updated
        self._radio_scheduler.set_recording_settings(updated)
        save_recording_settings(app_data_dir(), updated)
        self._announce("Recording settings saved")

    def _radio_open_schedule_recording(self) -> None:
        controller = getattr(self, "_radio_controller", None)
        station = controller.state.station if controller is not None else None
        ScheduleRecordingDialog(
            self.frame,
            entries=self._radio_scheduler.entries,
            default_station_name=station.name if station is not None else "",
            default_stream_url=station.stream_url if station is not None else "",
            on_add=self._radio_scheduler.add,
            on_remove=self._radio_scheduler.remove,
            on_update=self._radio_scheduler.update,
            favorites=self._radio_favorites,
            announce_cb=self._announce,
            windows=getattr(self, "_windows", None),
        ).show()
        # The next occurrence is now a different moment, so the OS wake that
        # was registered for the old one is wrong. Re-asked here rather than
        # per add/remove/update callback, so every path through the dialog --
        # including deleting the last entry -- lands on one refresh.
        self._refresh_radio_wake_task()
        self._update_sleep_inhibitor()

    def _refresh_radio_wake_task(self) -> None:
        """Re-register (or drop) the Windows wake for the next recording.
        See :mod:`quill.ui.radio.schedule_wake_ui`."""
        from quill.ui.radio import schedule_wake_ui

        schedule_wake_ui.refresh_wake_task(self)

    def _on_radio_state_changed(self, state: RadioPlaybackState) -> None:
        from quill.core.settings import save_settings

        self._radio_track_history_and_volume(state)
        self._radio_track_titles_follow_playback(state)
        self._radio_maybe_try_fallback_url(state)
        # A real playback transition re-arms the buffering earcon (#1302) --
        # volume/mute notifications land here too, and must not.
        if state.state is not getattr(self, "_radio_cued_playback_state", None):
            self._radio_cued_playback_state = state.state
            self._radio_buffer_cued = False
        if state.station is not None and not self._radio_ever_played:
            self._radio_ever_played = True
            hidden = list(getattr(self.settings, "status_bar_hidden", []))
            if "radio_player" in hidden:
                hidden.remove("radio_player")
                self.settings.status_bar_hidden = hidden
                save_settings(self.settings)
        self._refresh_statusbar()
        self._refresh_radio_tray_tooltip()
        self._update_sleep_inhibitor()

    def _update_sleep_inhibitor(self) -> None:
        """Keep the machine awake while a station plays or a recording runs (and
        the Prevent Sleep preference is on), releasing the request otherwise.
        Windows-only; a no-op elsewhere. Called on every playback/recording
        state change and when the preference is toggled."""
        from quill.platform.keep_awake import set_keep_awake
        from quill.ui.radio.player_controller import RadioPlayerState

        controller = getattr(self, "_radio_controller", None)
        playing = controller is not None and controller.state.state in (
            RadioPlayerState.PLAYING,
            RadioPlayerState.CONNECTING,
        )
        recorder = getattr(self, "_radio_recorder", None)
        recording = int(getattr(recorder, "active_count", 0) or 0) > 0
        # A scheduled recording cannot fire on a sleeping machine, and until
        # now nothing held standby off while merely *waiting* for one -- so a
        # computer that dozed at 10:58 started an 11:00 recording whenever it
        # next woke, which is indistinguishable from the app losing track of
        # time. See quill/core/radio/schedule_wake.py.
        from quill.ui.radio import schedule_wake_ui

        imminent = schedule_wake_ui.recording_is_imminent(self)
        want = (playing or recording or imminent) and bool(
            getattr(self._radio_history, "prevent_sleep", True)
        )
        if want == getattr(self, "_sleep_inhibited", False):
            return
        set_keep_awake(want)
        self._sleep_inhibited = want

    def _radio_track_history_and_volume(self, state: RadioPlaybackState) -> None:
        """Two memories, updated on every playback state change: the
        recently-played history (a newly started station moves to its front)
        and the per-station volume (a favorite remembers the volume you set
        while it plays -- restoring it on the way back in is
        RadioPlayerController's own job, via resolve_volume)."""
        station = state.station
        if station is None:
            self._radio_history_key = ""
            return
        key = station.station_uuid or station.stream_url
        favorite = self._radio_favorites.find(key)
        if key != self._radio_history_key:
            # A different station just started.
            self._radio_history_key = key
            self._radio_history.record(station)
            radio_history.save_history(app_data_dir(), self._radio_history)
            return
        if state.muted:
            return
        # Remember the last volume globally so it survives to the next launch
        # (#1263): without this a non-favorite station comes back at the 100%
        # default every time. Disk-only; the tree shows no volume.
        if state.volume_percent != self._radio_history.volume_percent:
            self._radio_history.volume_percent = state.volume_percent
            radio_history.save_history(app_data_dir(), self._radio_history)
        # A favorite additionally remembers its own per-station volume -- unless
        # one volume answers for every station, in which case the level just
        # saved above IS the answer and writing a per-station copy would quietly
        # rebuild the very per-station levels the setting exists to bypass.
        if getattr(self._radio_history, "use_global_volume", False):
            return
        if favorite is not None and state.volume_percent != favorite.volume_percent:
            self._radio_favorites.set_volume(key, state.volume_percent)
            # Disk-only (not _save_radio_favorites): the tree shows no volume,
            # and reloading it here re-announces the station on every Volume
            # Up/Down keystroke (#1154).
            self._persist_radio_favorites()

    # -- track titles (What's Playing) -----------------------------------------

    _TITLE_POLL_MS = 30000

    def _radio_track_titles_follow_playback(self, state: RadioPlaybackState) -> None:
        from quill.ui.radio.player_controller import RadioPlayerState

        timer = getattr(self, "_radio_title_timer", None)
        if timer is None:
            return
        if state.state is RadioPlayerState.PLAYING and state.station is not None:
            # A good connection also re-arms the one-shot stream fallback.
            self._radio_fallback_tried = ""
            if not timer.IsRunning():
                timer.Start(self._TITLE_POLL_MS)
                self._radio_fetch_track_title()
        else:
            timer.Stop()
            self._radio_track_title = ""

    def _radio_fetch_track_title(
        self,
        *,
        announce_result: bool = False,
        on_resolved: Callable[[], None] | None = None,
    ) -> None:
        """Read the playing stream's current title off-thread; announce a
        change when the user opted in, or unconditionally for an explicit
        What's Playing request.

        ``on_resolved`` (#1282) is called on the UI thread once the answer is
        in -- title or no title, success or failure -- so a caller waiting to
        copy or to open a window always gets its turn. Without it a failed
        fetch ended in silence, which is exactly how "the command does
        nothing" was reported.
        """
        from quill.core.radio.icy import read_stream_title

        controller = getattr(self, "_radio_controller", None)
        station = controller.state.station if controller is not None else None
        if station is None or self._safe_mode:
            if announce_result:
                self._announce("Nothing is playing.")
            if on_resolved is not None:
                on_resolved()
            return
        url = station.stream_url

        def _fetch(**_kwargs: object) -> str:
            return read_stream_title(url)

        def _done(_op: str, title: object) -> None:
            resolved = str(title or "")
            if not resolved and controller is not None:
                # Engine-native fallback (mpv media-title): some hosts
                # reject the out-of-band ICY tap, and HLS has no ICY at all.
                resolved = controller.engine_track_title()
            if not resolved:
                # Free tier-1 fallback (#1111): the station's own Icecast/
                # SHOUTcast status endpoint, off-thread. Only reached when both
                # ICY and the player gave nothing, so HLS streams (which the
                # player already titles) never make these extra requests.
                self._radio_fetch_server_now_playing(url, announce_result, on_resolved)
                return
            self._wx.CallAfter(
                self._radio_apply_track_title, resolved, announce_result, on_resolved
            )

        self._task_manager.submit(
            "radio-track-title",
            _fetch,
            on_success=_done,
            on_failure=lambda *_a: self._radio_title_fetch_failed(announce_result, on_resolved),
        )

    def _radio_title_fetch_failed(
        self, announce_result: bool, on_resolved: Callable[[], None] | None
    ) -> None:
        """A title fetch that errored still owes the listener an answer (#1282)."""
        self._wx.CallAfter(self._radio_apply_track_title, "", announce_result, on_resolved)

    def _radio_fetch_server_now_playing(
        self,
        url: str,
        announce_result: bool,
        on_resolved: Callable[[], None] | None = None,
    ) -> None:
        """Free #1111 fallback: read the current track from the station server's
        own status endpoint (Icecast/SHOUTcast) off-thread when ICY and the
        player exposed no title."""

        def _fetch(**_kwargs: object) -> str:
            from quill.core.radio.station_status import read_server_now_playing

            return read_server_now_playing(url, safe_mode=self._safe_mode)

        def _done(_op: str, title: object) -> None:
            self._wx.CallAfter(
                self._radio_apply_track_title, str(title or ""), announce_result, on_resolved
            )

        self._task_manager.submit(
            "radio-now-playing",
            _fetch,
            on_success=_done,
            on_failure=lambda *_a: self._radio_title_fetch_failed(announce_result, on_resolved),
        )

    def _radio_now_playing_phrase(self, title: str) -> str:
        """Render a raw stream title into the spoken announcement (#1068).

        Cleans up the raw broadcast metadata some stations send and applies the
        user's ``now_playing_template`` (see quill.core.radio.now_playing), so
        a wall of ``key="value"`` noise becomes "Now playing: YOUR SONG by
        Elton John"."""
        from quill.core.radio.now_playing import render_now_playing

        template = getattr(self._radio_history, "now_playing_template", "") or None
        phrase = render_now_playing(title, template) if template else render_now_playing(title)
        return f"Now playing: {phrase}"

    def _radio_apply_track_title(
        self,
        title: str,
        announce_result: bool,
        on_resolved: Callable[[], None] | None = None,
    ) -> None:
        changed = bool(title) and title != self._radio_track_title
        if title:
            self._radio_track_title = title
        if changed:
            # One choke point: every route to a title (ICY, the engine, the
            # station's status endpoint) lands here, and `changed` is already
            # the "this is a new song" signal the announcement uses.
            from quill.ui.radio import song_history_commands

            song_history_commands.record_song(self, title)
        if on_resolved is not None:
            # A waiting command (copy / review window) speaks for itself, so the
            # generic announcement is skipped -- two messages for one keystroke is
            # worse than none (#1282).
            on_resolved()
            return
        if announce_result:
            self._announce(
                self._radio_now_playing_phrase(title)
                if title
                else "This stream doesn't share track titles."
            )
            return
        if changed and self._radio_history.announce_track_titles:
            self._announce(self._radio_now_playing_phrase(title))

    # -- song history -----------------------------------------------------
    # Bodies live in quill.ui.radio.song_history_commands so this module stays
    # under its GATE-11 size budget (the same split quick_play uses).

    def radio_toggle_global_volume(self) -> None:
        """Turn "one volume for all stations" on or off."""
        from quill.ui.radio import volume_commands

        volume_commands.toggle_global_volume(self)

    def radio_forget_station_volumes(self) -> None:
        """Clear every favorite's own remembered volume, after confirming."""
        from quill.ui.radio import volume_commands

        volume_commands.forget_station_volumes(self)

    def radio_add_youtube_playlist(self) -> None:
        """List a YouTube playlist and add the videos you choose."""
        from quill.ui.radio.youtube_ui import add_youtube_playlist

        add_youtube_playlist(self)

    def radio_update_youtube_support(self) -> None:
        """Fetch a newer yt-dlp than the one bundled, when YouTube changes."""
        from quill.ui.radio.youtube_ui import update_youtube_support

        update_youtube_support(self)

    def radio_song_history(self) -> None:
        """Open the Song History window for the playing (or last) station."""
        from quill.ui.radio import song_history_commands

        song_history_commands.open_song_history(self)

    def radio_whats_playing(self) -> None:
        """Speak the current track title on demand."""
        if self._radio_track_title:
            self._announce(self._radio_now_playing_phrase(self._radio_track_title))
            return
        self._radio_fetch_track_title(announce_result=True)

    def _radio_now_playing_text(self) -> str:
        """The current now-playing title/artist as clean text -- no "Now
        playing:" prefix -- for copying or character-by-character review
        (#1134). Empty when nothing is playing / no title has been read yet."""
        from quill.core.radio.now_playing import render_now_playing

        title = self._radio_track_title
        if not title:
            return ""
        template = getattr(self._radio_history, "now_playing_template", "") or None
        return render_now_playing(title, template) if template else render_now_playing(title)

    def radio_copy_whats_playing(self) -> None:
        """Copy the current now-playing text to the clipboard (#1134, #1282)."""
        from quill.ui.radio.now_playing_commands import copy_whats_playing

        copy_whats_playing(self)

    def radio_whats_playing_details(self) -> None:
        """Open the reviewable, copyable What's Playing window (#1134, #1282)."""
        from quill.ui.radio.now_playing_commands import show_whats_playing_details

        show_whats_playing_details(self)

    def radio_now_playing_full_details(self) -> None:
        """Everything known about what's playing right now -- the station's own
        details (source, format, country, stream URL), the current track
        title/artist, and the live playback status -- in one reviewable,
        copyable window. This is the status bar's Now Playing action (Enter);
        with nothing on air it falls back to the track-only view."""
        controller = getattr(self, "_radio_controller", None)
        station = controller.state.station if controller is not None else None
        if station is None:
            self.radio_whats_playing_details()
            return
        track = self._radio_now_playing_text()
        lines = [
            station.details_text,
            "",
            f"Now playing: {track}" if track else "Now playing: no track information yet",
        ]
        state = controller.state
        volume = f"Volume: {int(getattr(state, 'volume_percent', 0) or 0)}%"
        if getattr(state, "muted", False):
            volume += " (muted)"
        if getattr(self._radio_history, "volume_boost", False):
            volume += " (boosted)"
        lines.append(volume)
        recorder = getattr(self, "_radio_recorder", None)
        count = int(getattr(recorder, "active_count", 0) or 0)
        if count:
            lines.append(f"Recording: {count} in progress")
        from quill.ui.radio.now_playing_dialog import NowPlayingDialog

        NowPlayingDialog(
            self.frame,
            "\n".join(lines),
            self._show_modal_dialog,
            self._copy_to_clipboard,
            self._announce,
            title=f"Now Playing: {station.display_name}",
        ).show()

    # -- live DVR (mpv engine): rewind / forward / back to live -----------------

    def radio_rewind(self) -> None:
        """Back 30 seconds -- along the video's timeline, or within the live buffer."""
        if self._radio_seek_bounded(-1):
            return
        behind = self._radio_controller.rewind(30)
        if behind is None:
            self._announce(self._radio_dvr_unavailable_message())
            return
        self._announce(f"Rewound 30 seconds. {self._radio_behind_live_phrase(behind)}")

    def radio_forward(self) -> None:
        """Forward 30 seconds -- along the timeline, or back toward the live edge."""
        if self._radio_seek_bounded(1):
            return
        behind = self._radio_controller.forward(30)
        if behind is None:
            self._announce(self._radio_dvr_unavailable_message())
            return
        self._announce(f"Forward 30 seconds. {self._radio_behind_live_phrase(behind)}")

    def _radio_seek_bounded(self, direction: int) -> bool:
        """Take the seek keys when a finished video is playing. True if taken.

        A live stream's DVR seek moves within mpv's *cache* and reports how
        far behind the live edge you are; a finished video has a real
        timeline. Sending a video down the DVR path announced a distance
        behind a live edge that does not exist -- a fabricated measurement
        (A-10) on the one source where the honest number was available.
        """
        if not self._radio_controller.is_seekable():
            return False
        from quill.ui.radio import bounded_playback_ui

        if direction > 0:
            bounded_playback_ui.skip_forward(self)
        else:
            bounded_playback_ui.skip_back(self)
        return True

    def radio_jump_to_live(self) -> None:
        """Return to the live edge of the stream."""
        if self._radio_controller.jump_to_live():
            self._announce("Back to live.")
        else:
            self._announce("Nothing is playing.")

    def _radio_dvr_unavailable_message(self) -> str:
        if self._radio_controller.state.station is None:
            return "Nothing is playing."
        return (
            "Rewinding live radio needs the mpv playback engine -- check "
            "Preferences > Playback engine."
        )

    @staticmethod
    def _radio_behind_live_phrase(behind: float) -> str:
        """A spoken 'how far behind live' fragment: 'Live.' under 5 seconds,
        else 'N seconds behind live.' / 'M minutes N seconds behind live.'"""
        seconds = int(round(behind))
        if seconds < 5:
            return "Live."
        if seconds < 60:
            return f"{seconds} seconds behind live."
        minutes, remainder = divmod(seconds, 60)
        plural = "" if minutes == 1 else "s"
        if remainder:
            return f"{minutes} minute{plural} {remainder} seconds behind live."
        return f"{minutes} minute{plural} behind live."

    def radio_toggle_volume_boost(self) -> None:
        """Volume Boost: amplify up to 50% past 100 for quiet streams
        (mpv engine). The 0-100 volume scale everywhere else is untouched."""
        history = self._radio_history
        history.volume_boost = not history.volume_boost
        radio_history.save_history(app_data_dir(), history)
        effective = self._radio_controller.set_volume_boost(history.volume_boost)
        if not history.volume_boost:
            self._announce("Volume Boost off.")
        elif effective:
            self._announce("Volume Boost on: up to 50 percent louder.")
        else:
            self._announce(
                "Volume Boost on. It takes effect on the mpv playback engine -- "
                "check Preferences > Playback engine."
            )

    def _radio_title_announce_command_title(self) -> str:
        """Palette label carrying the toggle's state -- it has no checkmark (#1383)."""
        state = "On" if self._radio_history.announce_track_titles else "Off"
        return f"Internet Radio: Announce Track Titles (currently {state})"

    def radio_toggle_title_announcements(self) -> None:
        history = self._radio_history
        history.announce_track_titles = not history.announce_track_titles
        radio_history.save_history(app_data_dir(), history)
        # Keep the palette entry honest about the new state (#1383).
        self.commands.set_title(
            "radio.toggle_title_announcements", self._radio_title_announce_command_title()
        )
        self._announce(
            "Track titles will be announced as they change."
            if history.announce_track_titles
            else "Track title announcements turned off."
        )

    # -- self-healing stream recovery (#1065) -----------------------------------

    def _radio_maybe_try_fallback_url(self, state: RadioPlaybackState) -> None:
        """A station whose stream fails heals itself (#1065).

        On a playback error, run the recovery ladder off-thread: re-resolve a
        moved StreamTheWorld mount, refresh from the directory, and -- unless
        the user turned it off -- scan the station's own website (Triton players
        and "Listen Live" links included). A confident hit is played
        automatically; anything ambiguous is announced so the user can pick it
        up in Find Streams. One attempt per station per session, so a truly dead
        station never loops."""
        from quill.ui.radio.player_controller import RadioPlayerState

        station = state.station
        if state.state is not RadioPlayerState.ERROR or station is None or self._safe_mode:
            return
        key = station.station_uuid or station.stream_url
        if self._radio_fallback_tried == key:
            return
        self._radio_fallback_tried = key
        allow_website = bool(getattr(self._radio_history, "recover_from_website", True))

        def _recover(**_kwargs: object) -> object:
            from quill.core.radio.recovery import recover_stream

            return recover_stream(station, allow_website=allow_website, safe_mode=self._safe_mode)

        def _done(_op: str, result: object) -> None:
            self._wx.CallAfter(self._radio_apply_recovery, result)

        self._task_manager.submit(
            "radio-stream-recovery",
            _recover,
            on_success=_done,
            on_failure=lambda *_a: None,
        )

    def _radio_apply_recovery(self, result: object) -> None:
        from quill.core.radio.recovery import RecoveryResult

        if not isinstance(result, RecoveryResult):
            return
        if result.station is not None:
            self._announce(result.message)
            # Self-heal the saved favorite so the next play starts from the good
            # URL, then play the healed station.
            favorite = self._radio_favorites.find(
                result.station.station_uuid or result.station.stream_url
            )
            if favorite is not None:
                favorite.station = result.station
                self._save_radio_favorites()
            self._radio_controller.play_station(result.station)
            return
        # No confident stream -- announce whatever we learned (candidates to
        # try via Find Streams, or simply that nothing was found).
        if result.message:
            self._announce(result.message)

    # -- wake-up timer ------------------------------------------------------------

    def _on_radio_wake_up(self, station: RadioStation) -> None:
        self._wx.CallAfter(self._apply_radio_wake_up, station)

    def _apply_radio_wake_up(self, station: RadioStation) -> None:
        self._radio_controller.play_station(station)
        self._announce(f"Good morning. {station.display_name} is coming on.")

    def open_wake_timer_dialog(self) -> None:
        """Wake-Up Timer...: the sleep timer's twin."""
        from quill.core.radio.wake_timer import load_wake_setting, save_wake_setting
        from quill.ui.radio.wake_timer_dialog import WakeUpTimerDialog

        controller = getattr(self, "_radio_controller", None)
        dialog = WakeUpTimerDialog(
            self.frame,
            setting=load_wake_setting(app_data_dir()),
            favorites=self._radio_favorites,
            now_playing=controller.state.station if controller is not None else None,
            announce_cb=self._announce,
        )
        updated = dialog.show()
        if updated is None:
            return
        save_wake_setting(app_data_dir(), updated)
        self._announce(updated.spoken_summary() if updated.enabled else "Wake-up timer turned off.")

    # -- record a different station ---------------------------------------------

    def open_record_station_dialog(self) -> None:
        """Record Station...: record B while listening to A (or to nothing)."""
        from quill.ui.radio.record_station_dialog import RecordStationDialog

        if not ffmpeg_available():
            self._show_message_box(
                self._radio_no_ffmpeg_message(),
                "Internet Radio",
                self._wx.ICON_INFORMATION | self._wx.OK,
            )
            return
        # Concurrent recording: no longer refuses when something is already
        # recording -- Record Station starts another capture alongside it.
        controller = getattr(self, "_radio_controller", None)
        dialog = RecordStationDialog(
            self.frame,
            favorites=self._radio_favorites,
            now_playing=controller.state.station if controller is not None else None,
            default_duration_minutes=min(60, self._radio_recording_settings.max_duration_minutes),
            announce_cb=self._announce,
        )
        choice = dialog.show()
        if choice is None:
            return
        station, minutes = choice
        try:
            self._radio_recorder.start(
                station_name=station.name,
                stream_url=station.stream_url,
                settings=self._radio_recording_settings,
                duration_minutes=minutes,
                filter_graph=self._radio_recording_filter_graph(),
                exact_optilab=self._radio_recording_exact(),
            )
        except RecordingError as error:
            self._announce(str(error))
            return
        self._announce(
            f"Recording started: {station.display_name}, for {minutes} minutes.",
            sound=SoundEvent.RADIO_RECORDING_STARTED,
        )
        self._refresh_statusbar()

    def radio_play_last(self) -> None:
        """Play whatever was on last -- radio as an appliance."""
        station = self._radio_history.last_station
        if station is None:
            self._announce("Nothing in the radio history yet. Play a station first.")
            return
        self._radio_controller.play_station(station)
        self._announce(f"Playing {station.display_name}")

    def _append_radio_recent_submenu(self, menu: object) -> None:
        """A Recently Played submenu: the last stations, newest first.

        Replaying a station never adds a second row -- the store moves the
        existing entry to the front (de-duplicated by uuid/stream URL). When
        a recent station is also a favorite, it speaks the favorite's own
        display name so the two menus never read like different stations.

        The submenu is always added (empty -> a disabled placeholder) and kept
        current by :meth:`_rebuild_recent_submenu` -- the standalone app rebuilds
        it each time the Station menu opens, so a station played after launch
        shows up without rebuilding the whole menu bar."""
        wx = self._wx
        sub = wx.Menu()
        self._recent_submenu = sub
        menu.AppendSubMenu(sub, "Recently &Played")
        self._rebuild_recent_submenu()

    def _rebuild_recent_submenu(self) -> None:
        """Repopulate the Recently Played submenu from current history (newest
        first). Safe to call repeatedly -- it clears the old items first, so it
        doubles as the live refresh (see ``_on_station_menu_open``)."""
        sub = getattr(self, "_recent_submenu", None)
        if sub is None:
            return
        wx = self._wx
        for item in list(sub.GetMenuItems()):
            sub.Delete(item)
        stations = list(self._radio_history.stations)
        if not stations:
            placeholder = sub.Append(wx.ID_ANY, "(none yet)")
            placeholder.Enable(False)
            return
        for station in stations:
            item_id = wx.NewIdRef()
            favorite = self._radio_favorites.find(station.station_uuid or station.stream_url)
            label = favorite.display_label if favorite is not None else station.display_name
            sub.Append(item_id, label)
            sub.Bind(
                wx.EVT_MENU,
                lambda _e, s=station: self._radio_controller.play_station(s),
                id=item_id,
            )
            self._retain_radio_menu_ids(item_id)

    def _refresh_radio_tray_tooltip(self) -> None:
        tray_icon = getattr(self, "_tray_icon", None)
        if tray_icon is None:
            return
        wx = self._wx
        # The tray icon's tooltip is also its accessible name: brand it with
        # the hosting app's own title ("Quill Radio" standalone, "Quill"
        # embedded) so tray navigation never reads the wrong product.
        app_name = self.frame.GetTitle() or "Quill"
        status = self._radio_status_text()  # carries "(recording)" when recording
        recorder = getattr(self, "_radio_recorder", None)
        recording = recorder is not None and bool(getattr(recorder, "active_count", 0))
        # R1/10.5: a recording always shows in the tray, even while playback is
        # stopped; idle (stopped, not recording) stays short (just the app name).
        if status and (recording or "stopped" not in status.lower()):
            tooltip = f"{app_name} - {status}"
        else:
            tooltip = app_name
        try:
            icon = getattr(self, "_app_icon", None) or wx.ArtProvider.GetIcon(
                wx.ART_INFORMATION, wx.ART_OTHER, (16, 16)
            )
            tray_icon.SetIcon(icon, tooltip)
        except Exception:  # noqa: BLE001 - tray tooltip refresh must never crash
            pass

    # -- status bar -----------------------------------------------------------

    def _radio_status_text(self) -> str:
        controller = getattr(self, "_radio_controller", None)
        if controller is None:
            return ""
        text = controller.state.status_text
        recorder = getattr(self, "_radio_recorder", None)
        count = int(getattr(recorder, "active_count", 0) or 0) if recorder is not None else 0
        if count == 1:
            text += " (recording)"
        elif count > 1:
            text += f" ({count} recording)"
        return text

    def radio_play_stop_toggle(self) -> None:
        """One transport action for menus rebuilt per popup: Stop while
        connecting/playing, resume when paused, replay the current station
        when stopped (live streams have no meaningful pause)."""
        from quill.ui.radio.player_controller import RadioPlayerState

        controller = getattr(self, "_radio_controller", None)
        if controller is None:
            return
        state = controller.state.state
        if state in (RadioPlayerState.PLAYING, RadioPlayerState.CONNECTING):
            self.radio_stop()
        else:
            self.radio_toggle_play_pause()

    def _build_radio_status_bar_menu(self, menu: object) -> None:
        from quill.ui.radio.player_controller import RadioPlayerState

        wx = self._wx
        play_id, mute_id = wx.NewIdRef(), wx.NewIdRef()
        controller = getattr(self, "_radio_controller", None)
        playing = controller is not None and controller.state.state in (
            RadioPlayerState.PLAYING,
            RadioPlayerState.CONNECTING,
        )
        # One transport item (this menu is rebuilt on every popup, so the
        # label is always current): Stop while playing, Play otherwise --
        # the same single-button rule as the main panel and Playback menu.
        menu.Append(play_id, "Stop" if playing else "Play")
        menu.Append(mute_id, "Mute/Unmute")
        menu.Bind(wx.EVT_MENU, lambda _e: self.radio_play_stop_toggle(), id=play_id)
        menu.Bind(wx.EVT_MENU, lambda _e: self.radio_mute_toggle(), id=mute_id)
        self._append_radio_favorites_submenu(menu)
        self._append_radio_recent_submenu(menu)
        menu.AppendSeparator()
        recorder = getattr(self, "_radio_recorder", None)
        record_id, schedule_id, rec_settings_id = wx.NewIdRef(), wx.NewIdRef(), wx.NewIdRef()
        # The label tracks the station you are listening to (concurrent
        # recording): Stop Recording only when *that* station is the one being
        # recorded, else Record Now.
        record_label = "Stop Recording" if self._radio_playing_job_id() else "Record Now"
        menu.Append(record_id, record_label)
        menu.Append(schedule_id, "Schedule Recording...")
        menu.Append(rec_settings_id, "Recording Settings...")
        menu.Bind(wx.EVT_MENU, lambda _e: self.radio_record_toggle(), id=record_id)
        menu.Bind(wx.EVT_MENU, lambda _e: self._radio_open_schedule_recording(), id=schedule_id)
        menu.Bind(wx.EVT_MENU, lambda _e: self._radio_open_recording_settings(), id=rec_settings_id)
        # Stop All appears only when two or more recordings are running.
        if int(getattr(recorder, "active_count", 0) or 0) >= 2:
            stop_all_id = wx.NewIdRef()
            menu.Append(stop_all_id, "Stop All Recordings")
            menu.Bind(wx.EVT_MENU, lambda _e: self.radio_stop_all_recordings(), id=stop_all_id)
        menu.AppendSeparator()
        browse_id = wx.NewIdRef()
        menu.Append(browse_id, "Browse Stations...")
        menu.Bind(wx.EVT_MENU, lambda _e: self.open_internet_radio(), id=browse_id)
        self._retain_radio_menu_ids(
            play_id, mute_id, record_id, schedule_id, rec_settings_id, browse_id
        )

    def _retain_radio_menu_ids(self, *refs: object) -> None:
        """Keep popup/submenu wx.NewIdRef objects alive while their menu can
        still fire. A dropped ref unreserves the id, and the next NewIdRef
        anywhere (another popup, an app-shell menu) can receive the same id --
        cross-wiring EVT_MENU bindings. Refs accumulate per host; rebuilt
        popups simply extend the list, which is bounded in practice."""
        refs_list = getattr(self, "_radio_menu_id_refs", None)
        if refs_list is None:
            refs_list = []
            self._radio_menu_id_refs = refs_list
        refs_list.extend(refs)

    # ACB Media and NFB Radio no longer have flat Station-menu builders: both are
    # first-class categories in Browse Stations (see browse_tree_dialog), which
    # reads the same bundled acb_media / nfb_media directories directly. The menu
    # copies only duplicated that and drifted stale, so they were removed.

    def _append_radio_favorites_submenu(self, menu: object) -> None:
        wx = self._wx
        favorites = getattr(self, "_radio_favorites", None)
        if favorites is None or not favorites.favorites:
            return
        sub = wx.Menu()
        # Mirror the Favorites Manager's nested folders: each folder path
        # ("News/Morning") becomes a nested submenu, stations appended to
        # their folder's menu in store order.
        folder_menus: dict[str, object] = {"": sub}

        def folder_menu(path: str) -> object:
            existing = folder_menus.get(path)
            if existing is not None:
                return existing
            parent_path, _, name = path.rpartition("/")
            parent = folder_menu(parent_path)
            child = wx.Menu()
            parent.AppendSubMenu(child, name)
            folder_menus[path] = child
            return child

        for favorite in favorites.favorites_in_display_order(
            self._radio_history.favorites_sort, self._radio_history.folder_sort_orders
        ):
            station = favorite.station
            item_id = wx.NewIdRef()
            folder_menu(favorite.folder).Append(item_id, favorite.display_label)
            sub.Bind(
                wx.EVT_MENU,
                lambda _e, s=station: self._radio_controller.play_station(s),
                id=item_id,
            )
            self._retain_radio_menu_ids(item_id)
        menu.AppendSubMenu(sub, "Favorite Stations")

    # -- system tray ----------------------------------------------------------

    def _build_radio_tray_menu(self, menu: object) -> None:
        wx = self._wx
        controller = getattr(self, "_radio_controller", None)
        now_playing_id = wx.NewIdRef()
        menu.Append(
            now_playing_id, controller.state.status_text if controller else "Radio: stopped"
        )
        menu.Enable(now_playing_id, False)
        self._retain_radio_menu_ids(now_playing_id)
        # Quick transport straight from the tray.
        play_id, stop_id = wx.NewIdRef(), wx.NewIdRef()
        menu.Append(play_id, "Play / Pause")
        menu.Append(stop_id, "Stop")
        menu.Bind(wx.EVT_MENU, lambda _e: self.radio_toggle_play_pause(), id=play_id)
        menu.Bind(wx.EVT_MENU, lambda _e: self.radio_stop(), id=stop_id)
        self._retain_radio_menu_ids(play_id, stop_id)
        self._build_radio_status_bar_menu(menu)
        # Reach the sibling apps without leaving the tray.
        menu.AppendSeparator()
        self._append_sibling_app_tray_items(menu, exclude="radio")

    # -- commands ---------------------------------------------------------

    def radio_toggle_play_pause(self) -> None:
        controller = getattr(self, "_radio_controller", None)
        if controller is None:
            return
        controller.toggle_play_pause()
        self._announce(controller.state.status_text)

    def radio_stop(self) -> None:
        controller = getattr(self, "_radio_controller", None)
        if controller is None:
            return
        controller.stop()
        self._announce("Radio stopped")

    def radio_mute_toggle(self) -> None:
        controller = getattr(self, "_radio_controller", None)
        if controller is None:
            return
        controller.toggle_mute()
        self._announce("Radio muted" if controller.state.muted else "Radio unmuted")

    def radio_volume_up(self) -> None:
        controller = getattr(self, "_radio_controller", None)
        if controller is None:
            return
        controller.volume_up()
        self._announce(f"Radio volume {controller.state.volume_percent}")

    def radio_volume_down(self) -> None:
        controller = getattr(self, "_radio_controller", None)
        if controller is None:
            return
        controller.volume_down()
        self._announce(f"Radio volume {controller.state.volume_percent}")

    def _on_radio_enhance_error(self, message: str) -> None:
        """Sound Enhancements couldn't start (ffmpeg missing, relay failed);
        playback still proceeds unenhanced, so this is an announcement, not a
        blocking dialog."""
        self._announce(f"Sound Enhancements: {message} Playing without it.")

    def _on_radio_output_device_error(self, message: str) -> None:
        """The chosen output device couldn't be used (libmpv missing or the
        engine failed); playback still proceeds on the system default, so
        this is an announcement, not a blocking dialog (#1076)."""
        self._announce(message)

    def _radio_resolve_enhancement(self, station: RadioStation) -> ResolvedEnhancement:
        """Every Sound Enhancements setting for *station*: its own remembered
        override if it's a favorite with one, else the shared default -- called
        by RadioPlayerController on every play_station. Every setting (EQ,
        compressor, channel mode, night mode, and OptiLab) is per-stream as well
        as global."""
        key = station.station_uuid or station.stream_url
        favorite = self._radio_favorites.find(key)
        if favorite is not None and favorite.has_sound_enhancement_override:
            return ResolvedEnhancement(
                bass_db=favorite.eq_bass_db,
                mid_db=favorite.eq_mid_db,
                treble_db=favorite.eq_treble_db,
                compressor_enabled=favorite.compressor_enabled,
                channel_mode=favorite.channel_mode,
                night_mode_enabled=favorite.night_mode_enabled,
                optilab_enabled=favorite.optilab_enabled,
                optilab_mode=favorite.optilab_mode,
                optilab_input_db=favorite.optilab_input_db,
                optilab_auto_adapt=favorite.optilab_auto_adapt,
                optilab_exact=favorite.optilab_exact,
                optilab_exact_live=favorite.optilab_exact_live,
            )
        history = self._radio_history
        return ResolvedEnhancement(
            bass_db=history.eq_bass_db,
            mid_db=history.eq_mid_db,
            treble_db=history.eq_treble_db,
            compressor_enabled=history.compressor_enabled,
            channel_mode=history.channel_mode,
            night_mode_enabled=history.night_mode_enabled,
            optilab_enabled=history.optilab_enabled,
            optilab_mode=history.optilab_mode,
            optilab_input_db=history.optilab_input_db,
            optilab_auto_adapt=history.optilab_auto_adapt,
            optilab_exact=history.optilab_exact,
            optilab_exact_live=history.optilab_exact_live,
        )

    def _radio_resolve_volume(self, station: RadioStation) -> int:
        """The volume (0-100) to play *station* at -- called by
        RadioPlayerController on every play_station.

        With "one volume for all stations" on, that single level answers for
        every station -- the whole point of it -- so it deliberately outranks a
        favorite's own remembered level, which is kept and wins again the moment
        the setting goes back off. Otherwise a favorite with its own level wins;
        failing that we fall back to the last volume the listener set globally,
        so a non-favorite plays at that level instead of snapping back to 100%
        on every launch (#1263). -1 (nothing ever set) still tells the controller
        to leave the current volume alone. getattr, because this runs on every
        play_station: a history predating the setting must fall through, never
        take playback down with an AttributeError."""
        if getattr(self._radio_history, "use_global_volume", False):
            return self._radio_history.volume_percent
        key = station.station_uuid or station.stream_url
        favorite = self._radio_favorites.find(key)
        if favorite is not None and favorite.volume_percent >= 0:
            return favorite.volume_percent
        return self._radio_history.volume_percent

    # -- YouTube (#1268) ----------------------------------------------------

    def _radio_youtube_consent(self) -> bool:
        """One-time consent before QUILL ever reaches YouTube (see youtube_ui)."""
        from quill.ui.radio.youtube_ui import ask_youtube_consent

        return ask_youtube_consent(self)

    def _radio_resolve_youtube(self, page_url: str) -> Any:
        """Resolve a saved YouTube link to a playable stream (worker thread).

        Returns the whole YouTubeStream so the controller can tell a finished
        video (seekable, chaptered) from a live broadcast (neither)."""
        from quill.ui.radio.youtube_ui import resolve_youtube_for_host

        return resolve_youtube_for_host(self, page_url)

    def _radio_enhance_context_favorite(self) -> FavoriteStation | None:
        """The favorite Sound Enhancements edits right now: the currently
        playing station, if it's a favorite -- None means edit the shared
        default instead (mirrors PodcastManagerDialog._sort_context_show)."""
        station = self._radio_controller.state.station
        if station is None:
            return None
        key = station.station_uuid or station.stream_url
        return self._radio_favorites.find(key)

    # -- dialogs ------------------------------------------------------------

    def open_media_sound_enhancements(self) -> None:
        """Ctrl+E: Sound Enhancements for whatever is playing. Wiring only --
        the rule lives in ui/media/sound_enhancements_route.py."""
        from quill.ui.media import sound_enhancements_route

        sound_enhancements_route.open_for_whats_playing(self)

    def open_sound_enhancements(self) -> None:
        """Playback > Sound Enhancements...: a three-band EQ + a compressor.
        Edits the currently-playing station's own override if it's a
        favorite, otherwise the shared default -- see
        RadioFavoritesStore.set_enhancement."""
        from quill.core.radio import history as radio_history
        from quill.ui.sound_enhance_dialog import SoundEnhanceDialog

        history = self._radio_history
        favorite = self._radio_enhance_context_favorite()
        override = favorite is not None and favorite.has_sound_enhancement_override
        # Every Sound Enhancements setting is per-stream as well as global: load
        # the playing favorite's own override if it has one, else the shared
        # default. FavoriteStation and RadioHistory share these field names.
        src: object = favorite if override else history
        bass = src.eq_bass_db
        mid = src.eq_mid_db
        treble = src.eq_treble_db
        compressor = src.compressor_enabled
        channel = src.channel_mode
        night = src.night_mode_enabled
        opt_enabled = src.optilab_enabled
        opt_mode = src.optilab_mode
        opt_input = src.optilab_input_db
        opt_adapt = src.optilab_auto_adapt
        opt_exact = src.optilab_exact
        opt_exact_live = src.optilab_exact_live
        on_reset = None
        if favorite is not None and favorite.has_sound_enhancement_override:

            def on_reset(favorite: FavoriteStation = favorite) -> None:
                self._radio_favorites.clear_enhancement_override(favorite.key)
                self._save_radio_favorites()
                state = self._radio_controller.state
                if (
                    state.station is not None
                    and (state.station.station_uuid or state.station.stream_url) == favorite.key
                ):
                    self._radio_controller.set_enhancement(
                        bass_db=history.eq_bass_db,
                        mid_db=history.eq_mid_db,
                        treble_db=history.eq_treble_db,
                        compressor_enabled=history.compressor_enabled,
                    )
                    self._radio_controller.set_sound_options(
                        channel_mode=history.channel_mode,
                        night_mode_enabled=history.night_mode_enabled,
                        optilab_enabled=history.optilab_enabled,
                        optilab_mode=history.optilab_mode,
                        optilab_input_db=history.optilab_input_db,
                        optilab_auto_adapt=history.optilab_auto_adapt,
                        optilab_exact_live=history.optilab_exact_live,
                    )
                self._announce(
                    f"Sound Enhancements for {favorite.display_label}: back to the shared default."
                )

        dialog = SoundEnhanceDialog(
            self.frame,
            bass_db=bass,
            mid_db=mid,
            treble_db=treble,
            compressor_enabled=compressor,
            subject=favorite.display_label if favorite is not None else "station",
            show_sound_options=True,
            channel_mode=channel,
            night_mode_enabled=night,
            optilab_enabled=opt_enabled,
            optilab_mode=opt_mode,
            optilab_input_db=opt_input,
            optilab_auto_adapt=opt_adapt,
            optilab_exact=opt_exact,
            optilab_exact_live=opt_exact_live,
            announce_cb=self._announce,
            on_reset=on_reset,
            on_live_change=self._radio_sound_preview,
        )
        result = dialog.show()
        if result is None:
            return
        bass_db, mid_db, treble_db, compressor_enabled, _smart_speed_not_applicable = result
        options = dialog.sound_options
        # Every setting is per-stream as well as global: when a favorite is
        # playing, all of it (EQ, compressor, channel, night mode, OptiLab) is
        # saved as that station's override; otherwise it updates the shared
        # default every other station follows.
        if favorite is not None:
            self._radio_favorites.set_enhancement(
                favorite.key,
                bass_db=bass_db,
                mid_db=mid_db,
                treble_db=treble_db,
                compressor_enabled=compressor_enabled,
                channel_mode=options.channel_mode,
                night_mode_enabled=options.night_mode_enabled,
                optilab_enabled=options.optilab_enabled,
                optilab_mode=options.optilab_mode,
                optilab_input_db=options.optilab_input_db,
                optilab_auto_adapt=options.optilab_auto_adapt,
                optilab_exact=options.optilab_exact,
                optilab_exact_live=options.optilab_exact_live,
            )
            self._save_radio_favorites()
            target = favorite.display_label
        else:
            history.eq_bass_db = bass_db
            history.eq_mid_db = mid_db
            history.eq_treble_db = treble_db
            history.compressor_enabled = compressor_enabled
            history.channel_mode = options.channel_mode
            history.night_mode_enabled = options.night_mode_enabled
            history.optilab_enabled = options.optilab_enabled
            history.optilab_mode = options.optilab_mode
            history.optilab_input_db = options.optilab_input_db
            history.optilab_auto_adapt = options.optilab_auto_adapt
            history.optilab_exact = options.optilab_exact
            history.optilab_exact_live = options.optilab_exact_live
            radio_history.save_history(app_data_dir(), history)
            target = "the shared default"
        # Apply the final values to what's playing (one apply for the whole set).
        self._radio_controller.preview_enhancements(
            bass_db=bass_db,
            mid_db=mid_db,
            treble_db=treble_db,
            compressor_enabled=compressor_enabled,
            channel_mode=options.channel_mode,
            night_mode_enabled=options.night_mode_enabled,
            optilab_enabled=options.optilab_enabled,
            optilab_mode=options.optilab_mode,
            optilab_input_db=options.optilab_input_db,
            optilab_auto_adapt=options.optilab_auto_adapt,
            optilab_exact_live=options.optilab_exact_live,
        )
        self._announce(
            f"Sound Enhancements for {target}: Bass {bass_db:+.0f}, Mid {mid_db:+.0f}, "
            f"Treble {treble_db:+.0f}" + (", Even Out Volume on" if compressor_enabled else "")
        )

    def _radio_sound_preview(self, snapshot: object) -> None:
        """Live-preview callback for the Sound Enhancements dialog: apply the
        in-progress settings to whatever is playing (mpv: live; wx: one
        reconnect) so the listener hears changes without pressing OK. Cancel
        reverts to the values captured when the dialog opened."""
        bass, mid, treble, compressor, _smart, options = snapshot  # type: ignore[misc]
        controller = getattr(self, "_radio_controller", None)
        if controller is None:
            return
        controller.preview_enhancements(
            bass_db=bass,
            mid_db=mid,
            treble_db=treble,
            compressor_enabled=compressor,
            channel_mode=options.channel_mode,
            night_mode_enabled=options.night_mode_enabled,
            optilab_enabled=options.optilab_enabled,
            optilab_mode=options.optilab_mode,
            optilab_input_db=options.optilab_input_db,
            optilab_auto_adapt=options.optilab_auto_adapt,
            optilab_exact_live=options.optilab_exact_live,
        )

    def open_manage_radio_favorites(self) -> None:
        """Manage Favorites...: search, play, remove, reorder, nested folders.

        Shared verbatim by embedded QUILL and standalone Quill Radio; every
        change persists immediately through the same store both read."""
        from quill.ui.radio.favorites_manager_dialog import FavoritesManagerDialog

        dlg = FavoritesManagerDialog(
            self.frame,
            favorites=self._radio_favorites,
            controller=self._radio_controller,
            announce_cb=self._announce,
            on_changed=self._save_radio_favorites,
            on_switch_to_manual=self._radio_switch_favorites_to_manual,
            sort=self._radio_history.favorites_sort,
            folder_sorts=self._radio_history.folder_sort_orders,
            windows=getattr(self, "_windows", None),
        )
        dlg.show()
        self._refresh_statusbar()

    def _radio_switch_favorites_to_manual(self) -> None:
        """Persist that favorites are now in manual order after the Favorites
        Manager reorders from a sorted view (the dialog bakes the store order;
        this records the sort switch in history so it survives a reload)."""
        from quill.core.paths import app_data_dir
        from quill.core.radio import history as radio_history

        self._radio_history.favorites_sort = "manual"
        self._radio_history.folder_sort_orders = {}
        radio_history.save_history(app_data_dir(), self._radio_history)

    def open_radio_recordings(self) -> None:
        """Recordings...: made, in-progress (live status), and scheduled."""
        from quill.ui.radio.recordings_manager_dialog import RecordingsManagerDialog

        dlg = RecordingsManagerDialog(
            self.frame,
            recorder=self._radio_recorder,
            settings=self._radio_recording_settings,
            scheduler=self._radio_scheduler,
            controller=self._radio_controller,
            announce_cb=self._announce,
            history=self._radio_history,
            on_history_changed=self._save_radio_history,
        )
        dlg.show()
        self._refresh_statusbar()

    def open_internet_radio(
        self, *, initial_category: str | None = None, focus_search: bool = False
    ) -> None:
        if self._safe_mode:
            self._show_message_box(
                _SAFE_MODE_MESSAGE, "Internet Radio", self._wx.ICON_INFORMATION | self._wx.OK
            )
            return
        dlg = StationBrowserDialog(
            self.frame,
            controller=self._radio_controller,
            favorites_store=self._radio_favorites,
            task_manager=self._task_manager,
            safe_mode=self._safe_mode,
            announce_cb=self._announce,
            on_favorites_changed=self._save_radio_favorites,
            on_open_add_custom=self._radio_open_add_custom,
            on_open_link_finder=self._radio_open_link_finder,
            on_report_bad_station=getattr(self, "report_bad_station", None),
            show_details=self._radio_history.show_station_details,
            windows=getattr(self, "_windows", None),
            spotify_client_provider=self._spotify_search_client,
            enabled_sources=self._radio_history.search_sources_enabled,
            catalog=_search_catalog(self),
            source_facet=self._radio_history.search_source_facet,
            on_search_prefs_changed=self._radio_save_search_prefs,
        )
        dlg.show(initial_category=initial_category, focus_search=focus_search)
        self._refresh_statusbar()

    def open_browse_stations(self, *, initial_source: str | None = None) -> None:
        """The dedicated, search-free Browse Stations tree: every source as a
        branch you expand to reveal its stations (Search Stations... stays the
        field-based dialog)."""
        if self._safe_mode:
            self._show_message_box(
                _SAFE_MODE_MESSAGE, "Internet Radio", self._wx.ICON_INFORMATION | self._wx.OK
            )
            return
        from quill.ui.radio import catalog_ui
        from quill.ui.radio.browse_tree_dialog import BrowseTreeDialog

        dlg = BrowseTreeDialog(
            self.frame,
            controller=self._radio_controller,
            favorites_store=self._radio_favorites,
            task_manager=self._task_manager,
            safe_mode=self._safe_mode,
            announce_cb=self._announce,
            on_favorites_changed=self._save_radio_favorites,
            on_report_bad_station=getattr(self, "report_bad_station", None),
            show_details=self._radio_history.show_station_details,
            windows=getattr(self, "_windows", None),
            # The app shell owns the one download queue (View > Downloads);
            # queueing on the dialog would start transfers no monitor can see.
            download_host=self,
            # Which branches to show. None means "never set" -> the defaults.
            visible_sources=self._radio_history.browse_sources_enabled,
            catalog=catalog_ui.catalog_for(self),
            on_offline_catalog=lambda: catalog_ui.note_offline_serving(self),
        )
        dlg.show(initial_source=initial_source)
        self._refresh_statusbar()

    def _radio_open_add_custom(self, prefill: RadioStation | None) -> None:
        dlg = AddStationDialog(
            self.frame,
            controller=self._radio_controller,
            prefill=prefill,
            announce_cb=self._announce,
            youtube_consent_cb=self._radio_youtube_consent,
        )
        station = dlg.show()
        if station is None:
            return
        self._radio_favorites.add(station, custom=True)
        self._save_radio_favorites()
        # Refresh the favorites tree and the favorite toggle so the just-added
        # custom station appears immediately, instead of only after a restart
        # (#1205). These live on the standalone RadioAppFrame; embedded QUILL
        # has no favorites tree, so guard for their absence.
        reload_tree = getattr(self, "_reload_favorites_tree", None)
        if callable(reload_tree):
            reload_tree()
        refresh_toggle = getattr(self, "_refresh_favorite_toggle", None)
        if callable(refresh_toggle):
            refresh_toggle()
        self._announce(f"Added {station.name} to Favorites", sound=SoundEvent.RADIO_FAVORITE_ADDED)

    def _radio_open_link_finder(self) -> None:
        if self._safe_mode:
            self._show_message_box(
                _SAFE_MODE_MESSAGE, "Internet Radio", self._wx.ICON_INFORMATION | self._wx.OK
            )
            return
        dlg = LinkFinderDialog(
            self.frame,
            controller=self._radio_controller,
            task_manager=self._task_manager,
            safe_mode=self._safe_mode,
            announce_cb=self._announce,
            on_use_link=self._radio_open_add_custom,
        )
        dlg.show()

    # -- command palette registration ----------------------------------------

    def _radio_play_favorite_slot(self, slot: int) -> None:
        """Play the slot-th favorite (1-based) -- the quick-play keys. Logic is in
        quill.ui.radio.quick_play so this module stays under the size budget."""
        quick_play.play_favorite_slot(
            slot,
            favorites=self._radio_favorites,
            history=self._radio_history,
            controller=self._radio_controller,
            announce=self._announce,
        )

    def _register_radio_commands(self) -> None:
        """Palette wiring lives in quill/ui/radio/palette_commands.py (GATE-11)."""
        from quill.ui.radio.palette_commands import register_radio_commands

        register_radio_commands(self)

    def open_spotify_connect(self) -> None:
        """Open the accessible Spotify sign-in dialog (Radio).
        Body in :mod:`quill.ui.radio.spotify_commands` (GATE-11)."""
        from quill.ui.radio import spotify_commands

        spotify_commands.connect(self)

    def _save_radio_history(self) -> None:
        """Persist RadioHistory. A failed save must never block the UI."""
        try:
            from quill.core.paths import app_data_dir
            from quill.core.radio import history as radio_history

            radio_history.save_history(app_data_dir(), self._radio_history)
        except Exception:  # noqa: BLE001 - a setting that did not persist is not fatal
            pass

    def radio_search_sources(self) -> None:
        """Choose which directories Find Stations searches (remembered).
        Body in :mod:`quill.ui.radio.settings_commands` (GATE-11)."""
        from quill.ui.radio import settings_commands

        settings_commands.search_sources(self)

    def radio_browse_sources_visibility(self) -> None:
        """Choose which branches Browse Stations shows (remembered)."""
        from quill.ui.radio import settings_commands

        settings_commands.browse_sources_visibility(self)

    def radio_download_preferences(self) -> None:
        """Where downloads land and how they are filed (remembered)."""
        from quill.ui.radio import settings_commands

        settings_commands.download_preferences(self)

    def radio_update_catalog(self) -> None:
        """Station > Update Station Catalog: refresh every due source now."""
        from quill.ui.radio import catalog_ui

        catalog_ui.update_catalog_command(self)

    def radio_catalog_status(self) -> None:
        """View > Station Catalog Status... See catalog_status_dialog."""
        from quill.ui.radio.catalog_status_dialog import show_catalog_status

        show_catalog_status(self)

    def _radio_save_search_prefs(self, enabled: tuple[str, ...], facet: str) -> None:
        """Remember the source selection and the Source facet across sessions."""
        self._radio_history.search_sources_enabled = enabled
        self._radio_history.search_source_facet = facet
        self._save_radio_history()

    def _spotify_search_client(self) -> object | None:
        """A signed-in Spotify client for Find Stations, or ``None``."""
        from quill.ui.radio import spotify_commands

        return spotify_commands.search_client(self)

    def open_spotify_browse(self) -> None:
        """Open the accessible Spotify browse dialog and play the chosen track."""
        from quill.ui.radio import spotify_commands

        spotify_commands.browse(self)
