"""Optional post-window services shared by every AppShell product."""

from __future__ import annotations

import logging
from collections.abc import Callable


class AppShellStartupMixin:
    """Failure-isolated release, maintenance, and sound initialization."""

    def _defer_startup_tasks(self, tasks: tuple[tuple[str, Callable[[], object]], ...]) -> None:
        from quill.ui import startup_launch

        startup_launch.defer_startup_tasks(
            self._wx,  # type: ignore[attr-defined]
            tasks,
            on_failure=self._report_startup_task_failure,
        )

    def _report_startup_task_failure(self, label: str) -> None:
        logging.getLogger(__name__).exception(
            "Optional startup task failed after %s was ready: %s",
            getattr(self, "_app_sounds_name", "the window"),
            label,
        )

    def _record_release_data_format(self) -> None:
        from quill.core.data_format_ledger import record_running_build

        record_running_build(self._startup_app_id, "")  # type: ignore[attr-defined]

    def _note_launch_for_maintenance(self) -> None:
        from quill.ui.maintenance_moment_ui import note_launch

        note_launch(self._startup_app_id)  # type: ignore[attr-defined]

    def _start_app_sounds(self) -> None:
        from quill.ui import app_sounds
        from quill.ui.companion_cues import init_app_sound

        init_app_sound(self.settings)  # type: ignore[attr-defined]
        app_sounds.apply(self)
