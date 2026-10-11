"""Show Cast before reading a large shared library, without exposing a blank profile."""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

from quill.core.podcasts.subscriptions import library_path, load_library
from quill.ui.podcasts.view_preparation import prepare_view

logger = logging.getLogger(__name__)
BACKGROUND_LOAD_ABOVE_BYTES = 256 * 1024


def needs_background_load(data_dir: Path) -> bool:
    try:
        return library_path(data_dir).stat().st_size > BACKGROUND_LOAD_ABOVE_BYTES
    except FileNotFoundError:
        return False
    except OSError:
        logger.exception("Could not inspect the podcast library; reading it on a worker")
        return True


class CastStartupLoadMixin:
    def _when_cast_library_ready(self, action: Callable[[], None]) -> None:
        if getattr(self, "_podcast_library_loading", False):
            self.__dict__.setdefault("_cast_ready_actions", []).append(action)
        else:
            self._wx.CallAfter(action)  # type: ignore[attr-defined]

    def _begin_cast_library_load(self) -> None:
        from quill.core.notifications import notifications_path
        from quill.core.paths import app_data_dir

        data_dir = app_data_dir()
        notice_path = notifications_path()
        mode = self._episode_show_filter()  # type: ignore[attr-defined]
        self._main_panel.Enable(False)  # type: ignore[attr-defined]
        self._set_status(  # type: ignore[attr-defined]
            "Loading your podcast library... You can still switch windows or close Cast."
        )

        def work(**_kwargs: Any) -> Any:
            from quill.ui.podcasts.launch_catchup import catch_up_with_radio

            library = load_library(data_dir, strict=True)
            handoff_error = ""
            try:
                catch_up_with_radio(library, data_dir=data_dir)
            except Exception:
                handoff_error = (
                    "The Quill Radio listening handoff could not be applied. "
                    "Your podcast library is still available."
                )
            place_id = library.settings.default_launch_view
            from quill.core.podcasts import places
            from quill.core.podcasts.virtual_views import iter_virtual_view_pairs

            if places.place(place_id) is None:
                place_id = "podcasts"
                for candidate in ("inbox", "continue_listening"):
                    if next(iter_virtual_view_pairs(library, candidate), None) is not None:
                        place_id = candidate
                        break
            prepared = prepare_view(
                library,
                place_id,
                episode_filter=mode,
                notifications_path=notice_path,
            )
            return library, place_id, prepared, handoff_error

        def loaded(_operation: str, result: Any) -> None:
            if (
                getattr(self, "_cast_closed", False)
                or getattr(self, "_cast_closing", False)
                or not self.frame  # type: ignore[attr-defined]
                or self.frame.IsBeingDeleted()  # type: ignore[attr-defined]
            ):
                return
            library, place_id, prepared, handoff_error = result
            self._podcast_library = library
            self._podcast_library_loading = False
            self._cast_place_counts = prepared.counts
            self._cast_unheard_counts = prepared.unheard
            self._cast_playlist_counts = prepared.playlist_counts
            self._cast_counts_revision = int(getattr(self, "_podcast_library_revision", 0))
            settings = library.settings
            self._podcast_controller.set_enhancement(  # type: ignore[attr-defined]
                bass_db=settings.eq_bass_db,
                mid_db=settings.eq_mid_db,
                treble_db=settings.eq_treble_db,
                compressor_enabled=settings.compressor_enabled,
                smart_speed_enabled=settings.smart_speed_enabled,
                channel_mode=settings.channel_mode,
            )
            if settings.output_device:
                if not self._podcast_controller.set_output_device(settings.output_device):  # type: ignore[attr-defined]
                    self._announce(  # type: ignore[attr-defined]
                        "The saved audio output could not be selected; using the current device."
                    )
            for queue in (self._podcast_download_queue, self._podcast_cache_queue):  # type: ignore[attr-defined]
                queue.set_reconnect_settings(
                    enabled=settings.reconnect_enabled,
                    max_attempts=settings.reconnect_max_attempts,
                    wait_seconds=settings.reconnect_wait_seconds,
                )
            self._rebuild_places()  # type: ignore[attr-defined]
            shown = [entry.id for entry in self._visible_places()]  # type: ignore[attr-defined]
            if place_id not in shown and shown:
                place_id = shown[0]
                self.show_place(place_id, focus=False)  # type: ignore[attr-defined]
            else:
                self._current_place = place_id
                self._places.select(place_id)  # type: ignore[attr-defined]
                self._content.show(  # type: ignore[attr-defined]
                    self._content.TREE if place_id == "podcasts" else self._content.LIST  # type: ignore[attr-defined]
                )
                self._apply_cast_prepared_view(prepared, (place_id, "", "", ""), None)  # type: ignore[attr-defined]
            self._main_panel.Enable(True)  # type: ignore[attr-defined]
            self._podcast_check_monitor.apply()  # type: ignore[attr-defined]
            self.podcast_run_maintenance(announce=False)  # type: ignore[attr-defined]
            self._refresh_statusbar()  # type: ignore[attr-defined]
            if handoff_error:
                self._announce(handoff_error)  # type: ignore[attr-defined]
            for action in self.__dict__.pop("_cast_ready_actions", []):
                self._wx.CallAfter(action)  # type: ignore[attr-defined]

        def failed(_operation: str, error: BaseException) -> None:
            if getattr(self, "_cast_closed", False) or getattr(self, "_cast_closing", False):
                return
            self._set_status(  # type: ignore[attr-defined]
                "Could not load the podcast library. Your saved library has not been replaced."
            )
            self._announce(  # type: ignore[attr-defined]
                f"Could not load the podcast library. Close and reopen Cast to retry. {error}"
            )

        self._cast_load_task = self._task_manager.submit(  # type: ignore[attr-defined]
            "cast-library-load",
            work,
            on_success=loaded,
            on_failure=failed,
            ui_lifetime=getattr(self, "_cast_ui_lifetime", None),
        )
