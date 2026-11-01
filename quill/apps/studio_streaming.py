"""Studio's Broadcast live commands: set up, check, go live, mute, stop (roadmap section 6).

Settings are remembered in ``studio-streams.json`` without the password, which
lives in Windows Credential Manager. Going live takes the shared microphone
lock when the microphone is in the stream, keeps the computer awake and turns
on Do Not Disturb for the length of the show, and restores both afterwards.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

import wx

_FILE = "studio-streams.json"


class StudioStreamingMixin:
    # -- sources the stream can carry --------------------------------------------------

    def _stream_choices(self, saved) -> tuple[list, dict]:
        """``(StreamSource rows, source_id -> SoundSource)`` for this moment."""
        from quill.core.demo_recording import SoundSource
        from quill.core.streaming import StreamSource

        kept = {s.source_id: s for s in saved}
        sound: dict = {}
        rows = []

        def add(source: SoundSource, *, reader: bool = False) -> None:
            before = kept.get(source.source_id)
            rows.append(
                StreamSource(
                    source.source_id,
                    source.label,
                    on=bool(before and before.on and not reader),
                    level_db=before.level_db if before else 0.0,
                    is_screen_reader=reader,
                )
            )
            sound[source.source_id] = source

        add(SoundSource("microphone", "Microphone", "microphone", enabled=True))
        readers = self._running_readers()
        reader_name, reader_pid = readers[0] if readers else ("", 0)
        add(
            SoundSource(
                "system",
                "System sound, without the screen reader" if reader_pid else "System sound",
                "system",
                enabled=True,
                exclude_process_id=reader_pid,
                exclude_name=reader_name,
            )
        )
        if reader_pid:
            add(
                SoundSource(
                    "screen_reader",
                    "Screen reader speech",
                    "screen-reader",
                    enabled=True,
                    process_id=reader_pid,
                    process_name=reader_name,
                ),
                reader=True,
            )
        try:
            from quill.platform.windows.audio_sessions import list_sessions

            for session in list_sessions():
                if session.process_id in (0, os.getpid(), reader_pid) or session.system_sounds:
                    continue
                add(
                    SoundSource(
                        "application",
                        f"{session.name.removesuffix('.exe')} sound",
                        f"app-{session.name.lower()}",
                        enabled=True,
                        process_id=session.process_id,
                        process_name=session.name,
                    )
                )
        except Exception:  # noqa: BLE001 - programs are optional; the basics remain
            pass
        return rows, sound

    def _stream_settings(self):
        from quill.core.paths import app_data_dir
        from quill.core.storage import read_json
        from quill.core.streaming import StreamSettings, settings_from_dict

        data = read_json(app_data_dir() / _FILE, {})
        try:
            return settings_from_dict(data) if isinstance(data, dict) and data else StreamSettings()
        except (TypeError, ValueError):
            return StreamSettings()

    @staticmethod
    def _stream_password(settings) -> str:
        from quill.core.streaming import credential_name
        from quill.platform.windows.credential_manager import load_generic_credential

        try:
            stored = load_generic_credential(credential_name(settings))
        except Exception:  # noqa: BLE001 - no stored password is a Stop, not a crash
            return ""
        return stored.secret if stored else ""

    # -- the window ----------------------------------------------------------------------

    def broadcast_live(self) -> None:
        if getattr(self, "_live", None) is not None:
            status = getattr(self, "_live_status", None)
            if status:
                status.Show()
                status.Raise()
            return
        ffmpeg = self._demo_ffmpeg()
        if not ffmpeg:
            self._announce("Broadcasting needs FFmpeg. Use Voices, Get FFmpeg.")
            return
        from dataclasses import replace

        from quill.ui.studio_go_live import GoLiveDialog

        saved = self._stream_settings()
        rows, sound = self._stream_choices(saved.sources)
        settings = replace(saved, sources=tuple(rows))
        if not settings.archive_folder:
            settings = replace(settings, archive_folder=str(self._demo_default_folder()))
        dialog = GoLiveDialog(
            self.frame,
            settings,
            self._stream_password(settings),
            check=self._check_stream,
            test=lambda s, p: self._test_stream(s, p, ffmpeg),
            confirm=lambda text, title: (
                self._show_message_box(text, title, wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING)
                in (wx.YES, wx.ID_YES)
            ),
        )
        try:
            if self._show_modal_dialog(dialog, "Broadcast live") != wx.ID_OK or not dialog.checked:
                return
            settings, password = dialog.checked
        finally:
            dialog.Destroy()
        self._start_stream(settings, password, sound, ffmpeg)

    def _check_stream(self, settings, password, done) -> None:
        from quill.core.streaming import can_start_stream, preflight, summary

        findings = preflight(settings, password=password)
        done(summary(settings, findings), can_start_stream(findings))

    def _test_stream(self, settings, password, ffmpeg) -> None:
        self._announce("Testing the connection.")

        def work(**_kwargs):
            from quill.platform.windows.live_stream import test_connection

            return test_connection(settings, password, ffmpeg)

        self._task_manager.submit(
            "Test a stream connection",
            work,
            on_success=lambda _t, problem: self._announce(
                problem or "The server accepted the test. Nobody heard it."
            ),
            on_failure=lambda _t, error: self._announce(f"The test could not run: {error}"),
            ui_lifetime=self._demo_lifetime(),
        )

    # -- live ------------------------------------------------------------------------

    def _start_stream(self, settings, password, sound, ffmpeg) -> None:
        from quill.core.demo_recording import unique_path
        from quill.core.paths import app_data_dir
        from quill.core.storage import write_json_atomic
        from quill.core.streaming import credential_name, settings_to_dict
        from quill.platform.windows.credential_manager import save_generic_credential
        from quill.platform.windows.live_stream import LiveStream

        try:
            save_generic_credential(credential_name(settings), password, user_name=settings.user)
        except Exception as error:  # noqa: BLE001 - going live still works this once
            self._announce(f"The password could not be remembered: {error}")
        try:
            write_json_atomic(app_data_dir() / _FILE, settings_to_dict(settings))
        except OSError:
            pass
        chosen = [sound[s.source_id] for s in settings.enabled() if s.source_id in sound]
        from dataclasses import replace as _replace

        levels = {s.source_id: s.level_db for s in settings.enabled()}
        chosen = [_replace(source, level_db=levels.get(source.source_id, 0.0)) for source in chosen]
        lock = None
        if any(source.kind == "microphone" for source in chosen):
            from quill.core.demo_recording import MICROPHONE_KEY
            from quill.core.dictation_owner import MicrophoneLock

            lock = MicrophoneLock("studio", key=MICROPHONE_KEY)
            refusal = lock.take()
            if refusal:
                self._announce(refusal)
                return
        archive = ""
        if settings.archive:
            name = (
                f"Show - {settings.title or settings.name} - {datetime.now():%Y-%m-%d %H%M%S}.flac"
            )
            archive = str(unique_path(Path(settings.archive_folder) / name))
            Path(settings.archive_folder).mkdir(parents=True, exist_ok=True)
        stream = LiveStream(
            settings,
            password,
            ffmpeg=ffmpeg,
            sources=chosen,
            on_event=lambda text, failure: wx.CallAfter(self._stream_event, text, failure),
            archive_path=archive,
            studio_pid=os.getpid(),
        )
        self._announce_settled("Going live.")

        def work(**_kwargs):
            stream.start()

        def live(_task, _result):
            from quill.ui.studio_live_status import LiveStatusFrame

            self._live, self._live_lock = stream, lock
            self._demo_quiet_start(_QuietPlan())
            self._live_status = LiveStatusFrame(
                status=stream.status_line,
                update_title=self._update_stream_title,
                mute=self.mute_broadcast,
                stop=self.stop_broadcast,
            )
            self._live_status.ShowWithoutActivating()
            # "On air." comes from the stream itself, once the server has taken
            # two seconds of audio (BCAST-027): a connection alone is not a show.

        def failed(_task, error):
            self._release_demo_microphone(lock)
            stream.stop()
            self._announce(f"Could not go live: {error}")

        self._task_manager.submit(
            "Go live", work, on_success=live, on_failure=failed, ui_lifetime=self._demo_lifetime()
        )

    def _stream_event(self, text: str, failure: bool) -> None:
        from quill.platform.windows.live_stream_air import BACK_ON_AIR, ON_AIR

        self._set_status_quiet(text)
        if failure or text in (ON_AIR, BACK_ON_AIR) or not getattr(self, "_live", None):
            self._announce(text)

    def _update_stream_title(self, title: str) -> None:
        stream = getattr(self, "_live", None)
        if stream is None or not title:
            return

        def work(**_kwargs):
            return stream.update_title(title)

        self._task_manager.submit(
            "Update the stream title",
            work,
            on_success=lambda _t, problem: self._announce(problem or "Title updated."),
            ui_lifetime=self._demo_lifetime(),
        )

    def mute_broadcast(self) -> None:
        stream = getattr(self, "_live", None)
        if stream is None:
            self._announce("Nothing is being broadcast.")
            return
        muted = not stream.mixer.public_muted
        stream.set_public_muted(muted)
        status = getattr(self, "_live_status", None)
        if status:
            status.set_muted(muted)
        self._announce_settled(
            "Everything public is muted." if muted else "Public sound is back on."
        )

    def stop_broadcast(self) -> None:
        stream = getattr(self, "_live", None)
        if stream is None:
            self._announce("Nothing is being broadcast.")
            return
        self._live = None
        status, self._live_status = getattr(self, "_live_status", None), None
        if status:
            status.finish()
        lock = getattr(self, "_live_lock", None)

        def work(**_kwargs):
            stream.stop()

        def done(_task, _result):
            self._release_demo_microphone(lock)
            self._demo_quiet_stop()
            # UX-013: state first, and the path only in the status bar.
            archive = stream.archive_path
            self._announce_settled(
                "Broadcast ended." + (" A copy was saved." if archive else ""),
                status=f"Broadcast ended. Saved copy: {archive}" if archive else "",
            )

        self._task_manager.submit(
            "Stop broadcasting",
            work,
            on_success=done,
            on_failure=done,
            ui_lifetime=self._demo_lifetime(),
        )

    def _stream_shutdown(self) -> None:
        stream = getattr(self, "_live", None)
        if stream is not None:
            self._live = None
            stream.stop()
            self._demo_quiet_stop()


class _QuietPlan:
    """A live show always keeps the computer awake and notifications quiet."""

    keep_awake = True
    do_not_disturb = True
