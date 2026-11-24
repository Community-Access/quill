"""QUILL's automatic maintenance waits for a quiet moment (FUX-15).

The launch check's "Update downloaded" window and the one-time component
questions asked at launch (the Braille Pack, Kokoro) go through
:func:`quill.ui.maintenance_moment_ui.offer_when_quiet`: never while dictating
or reading aloud, never in the first minute after launch, and never while
QUILL is not the window in front. Help > Check for Updates opens a held update
at once. A base of :class:`quill.ui.main_frame_updates.UpdatesMixin`, so the
updater's module stays inside its size budget (GATE-11).
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from quill.core.updates import GitHubRelease


class QuietMomentMixin:
    def _offer_when_quiet(
        self, kind: str, label: str, run: object, *, route: str, say: bool = True
    ) -> bool:
        """Open an automatic offer now, or hold it until a quiet moment (FUX-15).

        Held while dictating or reading aloud, in the first minute after
        launch, while typing, and while QUILL is not the window in front. The one sentence
        saying what waits goes to the status bar and Notifications, unspoken;
        ``say=False`` holds without it.
        """
        from quill.ui.maintenance_moment_ui import offer_when_quiet
        from quill.ui.maintenance_probes import probes_for

        def _note(line: str) -> None:
            if not say:
                return
            self._set_status_quiet(line)
            self._record_notification(line, "update")

        return offer_when_quiet(
            "quill",
            kind=kind,
            label=label,
            run=run,  # type: ignore[arg-type]
            route=route,
            window=self.frame,
            note=_note,
            probes=probes_for("quill", self),
            # The "waits" line stops being true as the offer opens.
            clear=(lambda: self._set_status_quiet("")) if say else None,
        )

    def _braille_pack_prompt_when_quiet(self) -> None:
        """Launch's Braille Pack question, held silently until quiet: it decides
        when it runs whether it is still owed, so a hold costs nothing."""
        self._offer_when_quiet(
            "braille-pack",
            "The Braille Pack question",
            self._maybe_prompt_braille_pack_install,  # type: ignore[attr-defined]
            route="",
            say=False,
        )

    def _kokoro_package_prompt_when_quiet(self) -> None:
        """Launch's Kokoro install question, held the same way."""
        self._offer_when_quiet(
            "kokoro-package",
            "The Kokoro install question",
            self._maybe_prompt_kokoro_package_install,  # type: ignore[attr-defined]
            route="",
            say=False,
        )

    def _update_download_voices(self, automatic: bool) -> tuple[Any, Any, Any]:
        """(speak, status, offer) for an update download: the launch check's
        progress is written and not spoken, and its offer waits for quiet."""
        if not automatic:
            return (
                self._announce,  # type: ignore[attr-defined]
                self._set_status,  # type: ignore[attr-defined]
                self._offer_post_download_actions,  # type: ignore[attr-defined]
            )
        return (lambda _message: None), self._set_status_quiet, self._offer_update_when_quiet  # type: ignore[attr-defined]

    def _offer_update_when_quiet(self, release: GitHubRelease, target: Path) -> None:
        """The launch check's "Update downloaded" window, at a quiet moment."""
        self._offer_when_quiet(
            "update",
            f"Update {release.version}",
            lambda: self._offer_post_download_actions(release, target),
            route="Help, Check for Updates offers it now.",
        )

    def _run_held_update_offer(self) -> bool:
        """Check for Updates asked for: a held, downloaded update opens now."""
        from quill.ui.maintenance_moment_ui import take_held

        run = take_held("quill", "update")
        if run is None:
            return False
        run()
        return True

    def _hold_background_update(self, target: object, state: object) -> bool:
        """Beta and Dev: the automatic download waits on a metered connection, in
        Quiet Hours, or while Quill Radio records; Stable is unchanged."""
        from quill.core.updater import history
        from quill.core.updater.background import background_gate, read_conditions

        gate = background_gate(state, read_conditions())  # type: ignore[arg-type]
        if not gate.reason:
            return False
        version = str(getattr(target, "version", ""))
        history.record("quill", "held_back", to_version=version, detail=gate.reason)
        self._record_notification(f"Update {version} found. {gate.reason}", "update")
        return True
