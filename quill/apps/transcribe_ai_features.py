"""QUILL Transcribe's AI task command, loaded without its agent dependencies."""

from __future__ import annotations

__all__ = ["TranscribeAiFeaturesMixin"]


class TranscribeAiFeaturesMixin:
    """The lightweight command hook mixed into the Transcribe product frame."""

    def cmd_ai_task(self) -> None:
        """Speakers, Sections and Summary (Ctrl+F3, codex.md 6.6)."""
        from quill.apps.transcribe_ai_task import (
            INSTRUCTION_HELP,
            SPEAKERS_AND_SECTIONS,
            STARTER,
            transcribe_task_facts,
            transcribe_task_tools,
        )

        self._open_app_task(  # type: ignore[attr-defined]
            SPEAKERS_AND_SECTIONS,
            lambda ctx: transcribe_task_tools(self, ctx),
            instruction_help=INSTRUCTION_HELP,
            starter=STARTER,
            context=lambda: transcribe_task_facts(self),
        )
