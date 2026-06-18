"""Pluggable watch-action registry (WATCH-2).

A watch *action* is the single operation a watch profile performs on each file
it claims. Actions implement a small, stable contract so new ones register
without touching the watch engine, and each action declares the feature id it
requires so the registry can gate it through the feature manager (FLAG-1).

This module is UI-framework-agnostic: no ``wx`` imports. The registry is the
seam that GLOW (WATCH-8) and BITS Whisperer (WATCH-9) plug into, and the same
seam the built-in actions (WATCH-7) use.
"""

from __future__ import annotations

import logging
import shutil
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

logger = logging.getLogger(__name__)

#: Outcome status values for a single action run.
OUTCOME_DONE = "done"
OUTCOME_FAILED = "failed"
OUTCOME_SKIPPED = "skipped"


def _humanize_action_error(action_id: str, error: BaseException) -> str:
    """Return a plain-language, screen-reader-friendly message for ``error``.

    Centralizes the M-1 humanization rule so every watch action surfaces an
    actionable message instead of a raw ``"[Errno 13] Permission denied: ..."``
    string. Falls back to ``str(error)`` for unrecognized categories so a new
    exception type is never hidden; the original is still logged via
    ``logger.exception`` at the call site.
    """
    if isinstance(error, PermissionError):
        return (
            f"Quill cannot complete the {action_id or 'watch'} action because it "
            "does not have permission to read or write the file or its folder. "
            "Try saving to a folder you own, or close the file if another "
            "program has it open."
        )
    if isinstance(error, FileNotFoundError):
        return (
            f"The file disappeared before the {action_id or 'watch'} action "
            "could finish. The watch will pick it up again if it reappears."
        )
    if isinstance(error, NotADirectoryError):
        return (
            f"A folder in the path is missing for the {action_id or 'watch'} "
            "action. Check that the destination folder still exists."
        )
    if isinstance(error, IsADirectoryError):
        return (
            f"The {action_id or 'watch'} action expected a file but found a "
            "folder. Remove the folder or pick a different destination."
        )
    if isinstance(error, OSError):
        # Disk full, path too long, sharing violation, etc. - keep the OS
        # message because it carries the actionable detail (e.g. Errno 28).
        return (
            f"The {action_id or 'watch'} action could not finish: {error.strerror or str(error)}."
        )
    return str(error)


@dataclass(frozen=True, slots=True)
class WatchItem:
    """One file claimed by a profile, handed to an action's ``run``."""

    source_path: Path
    profile_id: str = ""


@dataclass(frozen=True, slots=True)
class WatchActionOutcome:
    """The result of running an action on a single item."""

    status: str  # OUTCOME_DONE | OUTCOME_FAILED | OUTCOME_SKIPPED
    message: str = ""
    result_path: Path | None = None

    @property
    def ok(self) -> bool:
        return self.status == OUTCOME_DONE

    @classmethod
    def done(cls, message: str = "", result_path: Path | None = None) -> WatchActionOutcome:
        return cls(OUTCOME_DONE, message, result_path)

    @classmethod
    def failed(cls, message: str) -> WatchActionOutcome:
        return cls(OUTCOME_FAILED, message)

    @classmethod
    def skipped(cls, message: str) -> WatchActionOutcome:
        return cls(OUTCOME_SKIPPED, message)


@runtime_checkable
class WatchAction(Protocol):
    """The contract every watch action implements.

    Attributes
    ----------
    action_id:
        Stable identifier used to bind a profile to this action and to persist
        the choice. Never changes across releases.
    label:
        Short human-readable name for menus and the monitor.
    required_feature_id:
        Feature id this action needs; an empty string means always available.
    """

    action_id: str
    label: str
    required_feature_id: str
    requires_consent: bool

    def describe(self) -> str:
        """Return a plain-language sentence describing what the action does."""

    def preview(self, item: WatchItem, options: Mapping[str, object]) -> str:
        """Return what running the action on ``item`` would do, without side effects."""

    def validate(self, options: Mapping[str, object]) -> list[str]:
        """Return a list of human-readable problems with ``options`` (empty if valid)."""

    def run(self, item: WatchItem, options: Mapping[str, object]) -> WatchActionOutcome:
        """Perform the action for ``item`` and return its outcome."""


@dataclass(slots=True)
class _BaseAction:
    """Shared defaults so concrete actions only override what they need."""

    action_id: str = ""
    label: str = ""
    required_feature_id: str = ""
    description: str = ""
    requires_consent: bool = False

    def describe(self) -> str:
        return self.description

    def preview(self, item: WatchItem, options: Mapping[str, object]) -> str:  # noqa: ARG002
        return self.describe()

    def validate(self, options: Mapping[str, object]) -> list[str]:  # noqa: ARG002
        return []

    def run(self, item: WatchItem, options: Mapping[str, object]) -> WatchActionOutcome:
        raise NotImplementedError


@dataclass(slots=True)
class OpenAction(_BaseAction):
    """Built-in action: hand the file to the editor (WATCH-7).

    The actual open is performed by a caller-supplied callback so this stays
    UI-agnostic; the callback receives the source path and returns nothing.
    """

    action_id: str = "open"
    label: str = "Open in editor"
    description: str = "Open each detected file in a new editor tab."
    on_open: Callable[[Path], None] | None = None

    def validate(self, options: Mapping[str, object]) -> list[str]:  # noqa: ARG002
        if self.on_open is None:
            return ["No open handler is configured for this action."]
        return []

    def run(self, item: WatchItem, options: Mapping[str, object]) -> WatchActionOutcome:  # noqa: ARG002
        if self.on_open is None:
            return WatchActionOutcome.failed("No open handler is configured.")
        try:
            self.on_open(item.source_path)
        except Exception as error:  # surfaced as a failed outcome
            logger.exception("Open watch action failed for %s", item.source_path)
            return WatchActionOutcome.failed(_humanize_action_error(self.action_id, error))
        return WatchActionOutcome.done(f"Opened {item.source_path.name}")


@dataclass(slots=True)
class MoveAction(_BaseAction):
    """Built-in action: move each file to a destination folder (WATCH-7)."""

    action_id: str = "move"
    label: str = "Move to folder"
    description: str = "Move each detected file into a chosen destination folder."

    def validate(self, options: Mapping[str, object]) -> list[str]:
        destination = str(options.get("destination", "")).strip()
        if not destination:
            return ["Choose a destination folder for moved files."]
        if not Path(destination).expanduser().is_dir():
            return [f"Destination folder does not exist: {destination}"]
        return []

    def run(self, item: WatchItem, options: Mapping[str, object]) -> WatchActionOutcome:
        problems = self.validate(options)
        if problems:
            return WatchActionOutcome.failed(problems[0])
        destination = Path(str(options.get("destination", "")).strip()).expanduser()
        target = destination / item.source_path.name
        try:
            moved = shutil.move(str(item.source_path), str(target))
        except Exception as error:  # surfaced as a failed outcome
            logger.exception("Move watch action failed for %s", item.source_path)
            return WatchActionOutcome.failed(_humanize_action_error(self.action_id, error))
        return WatchActionOutcome.done(f"Moved to {target.name}", result_path=Path(moved))

    def preview(self, item: WatchItem, options: Mapping[str, object]) -> str:
        destination = str(options.get("destination", "")).strip() or "the chosen folder"
        return f"Move {item.source_path.name} into {destination}."


@dataclass(slots=True)
class CopyAction(_BaseAction):
    """Built-in action: copy each file to a destination, leaving the original (WATCH-7)."""

    action_id: str = "copy"
    label: str = "Copy to folder"
    description: str = (
        "Copy each detected file into a chosen destination folder, leaving the original in place."
    )

    def validate(self, options: Mapping[str, object]) -> list[str]:
        destination = str(options.get("destination", "")).strip()
        if not destination:
            return ["Choose a destination folder for copied files."]
        if not Path(destination).expanduser().is_dir():
            return [f"Destination folder does not exist: {destination}"]
        return []

    def preview(self, item: WatchItem, options: Mapping[str, object]) -> str:
        destination = str(options.get("destination", "")).strip() or "the chosen folder"
        return f"Copy {item.source_path.name} into {destination}."

    def run(self, item: WatchItem, options: Mapping[str, object]) -> WatchActionOutcome:
        problems = self.validate(options)
        if problems:
            return WatchActionOutcome.failed(problems[0])
        destination = Path(str(options.get("destination", "")).strip()).expanduser()
        target = destination / item.source_path.name
        try:
            copied = shutil.copy2(str(item.source_path), str(target))
        except Exception as error:  # surfaced as a failed outcome
            logger.exception("Copy watch action failed for %s", item.source_path)
            return WatchActionOutcome.failed(_humanize_action_error(self.action_id, error))
        return WatchActionOutcome.done(f"Copied to {target.name}", result_path=Path(copied))


@dataclass(slots=True)
class ConvertAction(_BaseAction):
    """Built-in action: export each file to a chosen format via a handler (WATCH-7).

    The conversion itself is performed by a caller-supplied callback (which wires
    in the IO writers and the bundled Pandoc), keeping this action UI-agnostic.
    The callback receives the source path and the target format id and returns
    the path of the converted file.
    """

    action_id: str = "convert"
    label: str = "Convert to another format"
    description: str = "Export each detected file to a chosen format."
    on_convert: Callable[[Path, str], Path] | None = None

    def validate(self, options: Mapping[str, object]) -> list[str]:
        if self.on_convert is None:
            return ["No conversion handler is configured for this action."]
        target_format = str(options.get("target_format", "")).strip()
        if not target_format:
            return ["Choose a target format for converted files."]
        return []

    def preview(self, item: WatchItem, options: Mapping[str, object]) -> str:
        target_format = str(options.get("target_format", "")).strip() or "the chosen format"
        return f"Convert {item.source_path.name} to {target_format}."

    def run(self, item: WatchItem, options: Mapping[str, object]) -> WatchActionOutcome:
        problems = self.validate(options)
        if problems:
            return WatchActionOutcome.failed(problems[0])
        assert self.on_convert is not None
        target_format = str(options.get("target_format", "")).strip()
        try:
            result = self.on_convert(item.source_path, target_format)
        except Exception as error:  # surfaced as a failed outcome
            logger.exception("Convert watch action failed for %s", item.source_path)
            return WatchActionOutcome.failed(_humanize_action_error(self.action_id, error))
        result_path = Path(result) if result else None
        name = result_path.name if result_path else target_format
        return WatchActionOutcome.done(f"Converted to {name}", result_path=result_path)


@dataclass(slots=True)
class RunMacroAction(_BaseAction):
    """Built-in action: open each file and run a saved macro over it (WATCH-7, FEAT-7).

    Macros replay editor command ids, so the actual replay is delegated to a
    caller-supplied handler that owns the editor; this action stays wx-free.
    """

    action_id: str = "run_macro"
    label: str = "Run a macro"
    description: str = "Open each detected file and run a saved macro over it."
    on_run_macro: Callable[[Path, str], None] | None = None

    def validate(self, options: Mapping[str, object]) -> list[str]:
        if self.on_run_macro is None:
            return ["No macro handler is configured for this action."]
        macro_name = str(options.get("macro_name", "")).strip()
        if not macro_name:
            return ["Choose a macro to run."]
        return []

    def preview(self, item: WatchItem, options: Mapping[str, object]) -> str:
        macro_name = str(options.get("macro_name", "")).strip() or "the chosen macro"
        return f"Run macro '{macro_name}' on {item.source_path.name}."

    def run(self, item: WatchItem, options: Mapping[str, object]) -> WatchActionOutcome:
        problems = self.validate(options)
        if problems:
            return WatchActionOutcome.failed(problems[0])
        assert self.on_run_macro is not None
        macro_name = str(options.get("macro_name", "")).strip()
        try:
            self.on_run_macro(item.source_path, macro_name)
        except Exception as error:  # surfaced as a failed outcome
            logger.exception("Run-macro watch action failed for %s", item.source_path)
            return WatchActionOutcome.failed(_humanize_action_error(self.action_id, error))
        return WatchActionOutcome.done(f"Ran macro '{macro_name}' on {item.source_path.name}")


@dataclass(slots=True)
class RunPythonTransformAction(_BaseAction):
    """Built-in action: run a saved, sandboxed Python transform on each file (WATCH-7, SEC-9).

    The transform reads the file's text as ``document_text`` and sets ``result``;
    the sandbox enforces import and wall-clock limits. The sandbox runner is
    injectable so tests need not spawn a subprocess.
    """

    action_id: str = "run_python"
    label: str = "Run a Python transform"
    description: str = "Run a saved, sandboxed Python transform over each detected file's text."
    runner: Callable[..., object] | None = None
    default_timeout_seconds: float = 5.0

    def _resolve_runner(self) -> Callable[..., object]:
        if self.runner is not None:
            return self.runner
        from .python_sandbox import run_python_sandbox

        return run_python_sandbox

    def validate(self, options: Mapping[str, object]) -> list[str]:
        code = str(options.get("code", "")).strip()
        if not code:
            return ["Provide the Python transform code to run."]
        return []

    def preview(self, item: WatchItem, options: Mapping[str, object]) -> str:  # noqa: ARG002
        return f"Run the saved Python transform over {item.source_path.name} (sandboxed)."

    def run(self, item: WatchItem, options: Mapping[str, object]) -> WatchActionOutcome:
        problems = self.validate(options)
        if problems:
            return WatchActionOutcome.failed(problems[0])
        code = str(options.get("code", ""))
        try:
            text = item.source_path.read_text(encoding="utf-8")
        except OSError as error:
            return WatchActionOutcome.failed(f"Could not read file: {error}")
        raw_timeout = options.get("timeout_seconds", self.default_timeout_seconds)
        try:
            timeout_seconds = max(0.1, float(raw_timeout))  # type: ignore[arg-type]
        except (TypeError, ValueError):
            timeout_seconds = self.default_timeout_seconds
        runner = self._resolve_runner()
        try:
            result = runner(code, document_text=text, timeout_seconds=timeout_seconds)
        except Exception as error:  # surfaced as a failed outcome
            logger.exception("Python transform watch action failed for %s", item.source_path)
            return WatchActionOutcome.failed(_humanize_action_error(self.action_id, error))
        if not getattr(result, "succeeded", False):
            message = (
                getattr(result, "error", "")
                or getattr(result, "stderr", "")
                or "The transform did not complete."
            )
            return WatchActionOutcome.failed(message)
        output = getattr(result, "result", "") or getattr(result, "stdout", "")
        suffix = str(options.get("output_suffix", "")).strip()
        if suffix:
            target = item.source_path.with_name(
                item.source_path.stem + suffix + item.source_path.suffix
            )
        else:
            target = item.source_path
        try:
            target.write_text(output, encoding="utf-8")
        except OSError as error:
            return WatchActionOutcome.failed(f"Could not write transformed file: {error}")
        return WatchActionOutcome.done(f"Transformed {item.source_path.name}", result_path=target)


@dataclass(slots=True)
class AiAction(_BaseAction):
    """Built-in action: run a consented AI action over each file (WATCH-7, AI-5, WATCH-6).

    Marked ``requires_consent`` so the registry refuses to run it until the
    profile carries explicit per-profile consent (``options["consent"] is True``),
    honoring the no-silent-network rule. The AI call itself is delegated to a
    caller-supplied handler that returns a finished outcome.
    """

    action_id: str = "ai"
    label: str = "Run an AI action"
    description: str = (
        "Run a consented AI action (summarize, tag, or rewrite) over each detected file."
    )
    requires_consent: bool = True
    on_ai: Callable[[Path, Mapping[str, object]], WatchActionOutcome] | None = None

    def validate(self, options: Mapping[str, object]) -> list[str]:
        if self.on_ai is None:
            return ["No AI handler is configured for this action."]
        mode = str(options.get("mode", "")).strip().lower()
        if mode not in {"summarize", "tag", "rewrite"}:
            return ["Choose an AI mode: summarize, tag, or rewrite."]
        return []

    def preview(self, item: WatchItem, options: Mapping[str, object]) -> str:
        mode = str(options.get("mode", "")).strip().lower() or "the chosen AI action"
        return (
            f"Run the AI {mode} action on {item.source_path.name} "
            "(requires consent; sends content to the AI provider)."
        )

    def run(self, item: WatchItem, options: Mapping[str, object]) -> WatchActionOutcome:
        problems = self.validate(options)
        if problems:
            return WatchActionOutcome.failed(problems[0])
        assert self.on_ai is not None
        try:
            outcome = self.on_ai(item.source_path, options)
        except Exception as error:  # surfaced as a failed outcome
            logger.exception("AI watch action failed for %s", item.source_path)
            return WatchActionOutcome.failed(_humanize_action_error(self.action_id, error))
        if not isinstance(outcome, WatchActionOutcome):
            return WatchActionOutcome.failed("AI handler returned an invalid result.")
        return outcome


@dataclass(slots=True)
class OcrAction(_BaseAction):
    """Built-in action: OCR an arriving image into an editable text file (OCR-5).

    Gated by the ``core.ocr`` feature and offline by default, so it carries no
    ``requires_consent`` (OCR never leaves the machine). Recognition is
    delegated to an injected ``on_ocr`` handler that returns the recognized
    text for an image path, keeping the platform/WinRT details out of core.
    """

    action_id: str = "ocr"
    label: str = "OCR image to text"
    description: str = "Recognize text in each arriving image and save it as a text file."
    required_feature_id: str = "core.ocr"
    on_ocr: Callable[[Path], str] | None = None
    output_suffix: str = ".txt"

    def validate(self, options: Mapping[str, object]) -> list[str]:  # noqa: ARG002
        if self.on_ocr is None:
            return ["No OCR engine is configured for this action."]
        return []

    def preview(self, item: WatchItem, options: Mapping[str, object]) -> str:  # noqa: ARG002
        return f"Recognize text in {item.source_path.name} and save it next to the image (offline)."

    def run(self, item: WatchItem, options: Mapping[str, object]) -> WatchActionOutcome:  # noqa: ARG002
        if self.on_ocr is None:
            return WatchActionOutcome.failed("No OCR engine is configured for this action.")
        try:
            text = self.on_ocr(item.source_path)
        except Exception as error:  # surfaced as a failed outcome
            logger.exception("OCR watch action failed for %s", item.source_path)
            return WatchActionOutcome.failed(_humanize_action_error(self.action_id, error))
        target = item.source_path.with_suffix(self.output_suffix)
        body = text if text.endswith("\n") else text + "\n"
        try:
            target.write_text(body, encoding="utf-8")
        except OSError as error:
            return WatchActionOutcome.failed(f"Could not write recognized text: {error}")
        return WatchActionOutcome.done(
            f"Recognized text from {item.source_path.name}", result_path=target
        )


@dataclass(slots=True)
class UnavailableAction(_BaseAction):
    """Placeholder for an action whose engine has not landed yet (WATCH-8/9).

    It registers under a stable id and feature, but always reports itself
    unavailable with an announced reason until the real action replaces it.
    """

    reason: str = "This action is not available yet."

    def validate(self, options: Mapping[str, object]) -> list[str]:  # noqa: ARG002
        return [self.reason]

    def run(self, item: WatchItem, options: Mapping[str, object]) -> WatchActionOutcome:  # noqa: ARG002
        return WatchActionOutcome.skipped(self.reason)


class WatchActionRegistry:
    """A typed registry mapping action ids to actions, with feature gating."""

    def __init__(self, *, feature_enabled: Callable[[str], bool] | None = None) -> None:
        self._actions: dict[str, WatchAction] = {}
        self._feature_enabled = feature_enabled

    def register(self, action: WatchAction, *, replace: bool = False) -> None:
        """Register ``action`` under its ``action_id``.

        Raises :class:`ValueError` on a duplicate id unless ``replace`` is set,
        which lets a real action (e.g. GLOW) supersede its placeholder.
        """
        action_id = action.action_id
        if not action_id:
            raise ValueError("Watch action must declare a non-empty action_id.")
        if action_id in self._actions and not replace:
            raise ValueError(f"Watch action id already registered: {action_id}")
        self._actions[action_id] = action

    def get(self, action_id: str) -> WatchAction | None:
        return self._actions.get(action_id)

    def actions(self) -> list[WatchAction]:
        """Every registered action, ordered by id for stable presentation."""
        return [self._actions[key] for key in sorted(self._actions)]

    def is_feature_enabled(self, action: WatchAction) -> bool:
        feature_id = action.required_feature_id
        if not feature_id:
            return True
        if self._feature_enabled is None:
            return True
        return bool(self._feature_enabled(feature_id))

    def available_actions(self) -> list[WatchAction]:
        """Registered actions whose required feature is currently enabled."""
        return [action for action in self.actions() if self.is_feature_enabled(action)]

    def is_available(self, action_id: str) -> bool:
        action = self.get(action_id)
        return action is not None and self.is_feature_enabled(action)

    def run(
        self,
        action_id: str,
        item: WatchItem,
        options: Mapping[str, object] | None = None,
    ) -> WatchActionOutcome:
        """Validate, gate, then run ``action_id`` for ``item``.

        Returns a ``failed`` outcome for an unknown action or invalid options,
        and a ``skipped`` outcome when the action's feature is disabled, so the
        queue always receives a definite result rather than an exception.
        """
        action = self.get(action_id)
        if action is None:
            return WatchActionOutcome.failed(f"Unknown watch action: {action_id}")
        if not self.is_feature_enabled(action):
            return WatchActionOutcome.skipped(
                f"The feature for action '{action.label}' is turned off."
            )
        opts: Mapping[str, object] = options or {}
        if getattr(action, "requires_consent", False) and not bool(opts.get("consent")):
            return WatchActionOutcome.skipped(
                f"Action '{action.label}' needs per-profile consent before it can run."
            )
        problems = action.validate(opts)
        if problems:
            return WatchActionOutcome.failed(problems[0])
        try:
            return action.run(item, opts)
        except Exception as error:  # last-resort guard so one file never crashes the loop
            logger.exception("Watch action %s crashed for %s", action_id, item.source_path)
            return WatchActionOutcome.failed(_humanize_action_error(action_id, error))

    def dry_run(
        self,
        action_id: str,
        item: WatchItem,
        options: Mapping[str, object] | None = None,
    ) -> str:
        """Describe what running ``action_id`` for ``item`` would do, with no side effects.

        Returns the action's preview when it would run, or a plain-language reason
        it would not (unknown id, disabled feature, invalid options, or missing
        consent). Powers a profile's dry-run preview (WATCH-6).
        """
        action = self.get(action_id)
        if action is None:
            return f"Unknown watch action: {action_id}"
        if not self.is_feature_enabled(action):
            return f"The feature for action '{action.label}' is turned off, so nothing would run."
        opts: Mapping[str, object] = options or {}
        problems = action.validate(opts)
        if problems:
            return f"Would not run: {problems[0]}"
        if getattr(action, "requires_consent", False) and not bool(opts.get("consent")):
            return f"Would not run: action '{action.label}' needs per-profile consent first."
        return action.preview(item, opts)


def default_registry(
    *,
    feature_enabled: Callable[[str], bool] | None = None,
    on_open: Callable[[Path], None] | None = None,
    on_convert: Callable[[Path, str], Path] | None = None,
    on_run_macro: Callable[[Path, str], None] | None = None,
    on_ai: Callable[[Path, Mapping[str, object]], WatchActionOutcome] | None = None,
    on_ocr: Callable[[Path], str] | None = None,
    sandbox_runner: Callable[..., object] | None = None,
) -> WatchActionRegistry:
    """Build a registry pre-populated with the built-in actions and placeholders."""
    registry = WatchActionRegistry(feature_enabled=feature_enabled)
    registry.register(OpenAction(on_open=on_open))
    registry.register(MoveAction())
    registry.register(CopyAction())
    registry.register(ConvertAction(on_convert=on_convert))
    registry.register(RunMacroAction(on_run_macro=on_run_macro))
    registry.register(RunPythonTransformAction(runner=sandbox_runner))
    registry.register(AiAction(on_ai=on_ai))
    registry.register(OcrAction(on_ocr=on_ocr))
    registry.register(
        UnavailableAction(
            action_id="glow_audit",
            label="Audit and fix accessibility (GLOW)",
            required_feature_id="future.glow",
            description="Run the GLOW audit-and-fix flow over each arriving document.",
            reason="GLOW accessibility auditing is not available yet.",
        )
    )
    registry.register(
        UnavailableAction(
            action_id="bw_transcribe",
            label="Transcribe audio (BITS Whisperer)",
            required_feature_id="future.bits_whisperer",
            description="Transcribe arriving audio into an editable document.",
            reason="BITS Whisperer transcription is not available yet.",
        )
    )
    registry.register(CloudTranscribeAction())
    return registry


@dataclass(slots=True)
class CloudTranscribeAction(_BaseAction):
    """Watch action: transcribe arriving audio via OpenAI Whisper (AI-cloud).

    Gated by ``future.ai`` and requires an OpenAI API key stored in the
    credential manager. Sends audio bytes to the OpenAI transcription endpoint
    (GATE-9 reviewed: ``transcription.py::_post_audio``). The user must have
    enabled AI and configured an OpenAI API key — no silent transcription.

    The action writes a sibling ``.txt`` file next to the audio file.
    Supported extensions: .mp3, .mp4, .m4a, .wav, .webm, .ogg, .flac.
    Files over 25 MB are skipped with a OUTCOME_SKIPPED outcome.
    """

    action_id: str = "cloud_transcribe"
    label: str = "Transcribe audio (OpenAI Whisper)"
    description: str = (
        "Transcribe arriving audio files via OpenAI Whisper and save the transcript "
        "as a text file next to the audio. Requires an OpenAI API key."
    )
    required_feature_id: str = "future.ai"
    requires_consent: bool = True
    output_suffix: str = ".txt"

    def describe(self) -> str:
        return self.description

    def preview(self, item: WatchItem, options: Mapping[str, object]) -> str:  # noqa: ARG002
        return (
            f"Transcribe {item.source_path.name} via OpenAI Whisper and save "
            f"the transcript as {item.source_path.stem}.txt next to the audio file."
        )

    def validate(self, options: Mapping[str, object]) -> list[str]:  # noqa: ARG002
        problems: list[str] = []
        try:
            from quill.core.assistant_ai import load_assistant_api_key

            if not load_assistant_api_key():
                problems.append(
                    "No OpenAI API key is configured. "
                    "Add one in AI Hub before using cloud transcription."
                )
        except Exception:  # noqa: BLE001
            problems.append("Could not check API key configuration.")
        return problems

    def run(self, item: WatchItem, options: Mapping[str, object]) -> WatchActionOutcome:
        from quill.core.ai.transcription import (
            MAX_FILE_SIZE_BYTES,
            SUPPORTED_AUDIO_EXTENSIONS,
            TranscriptionError,
            TranscriptionFileTooLargeError,
            TranscriptionFormatError,
            transcribe_file,
        )
        from quill.core.assistant_ai import load_assistant_api_key

        path = item.source_path
        if path.suffix.lower() not in SUPPORTED_AUDIO_EXTENSIONS:
            return WatchActionOutcome.skipped(
                f"{path.name} is not a supported audio format. Skipped."
            )

        size = path.stat().st_size if path.exists() else 0
        if size > MAX_FILE_SIZE_BYTES:
            size_mb = size / (1024 * 1024)
            return WatchActionOutcome.skipped(
                f"{path.name} is {size_mb:.1f} MB, which exceeds the 25 MB cloud limit. Skipped."
            )

        api_key = load_assistant_api_key() or ""
        if not api_key:
            return WatchActionOutcome.failed(
                "No OpenAI API key configured. Add one in AI Hub to use cloud transcription."
            )

        language = str(options.get("language", "")) or None
        try:
            transcript = transcribe_file(path, api_key, language=language)
        except TranscriptionFileTooLargeError as exc:
            return WatchActionOutcome.skipped(str(exc))
        except TranscriptionFormatError as exc:
            return WatchActionOutcome.skipped(str(exc))
        except TranscriptionError as exc:
            logger.exception("Cloud transcription failed for %s", path)
            return WatchActionOutcome.failed(f"Transcription failed: {exc}")
        except Exception as exc:  # noqa: BLE001
            logger.exception("Cloud transcription crashed for %s", path)
            return WatchActionOutcome.failed(_humanize_action_error(self.action_id, exc))

        target = path.with_suffix(self.output_suffix)
        body = transcript if transcript.endswith("\n") else transcript + "\n"
        try:
            target.write_text(body, encoding="utf-8")
        except OSError as exc:
            return WatchActionOutcome.failed(f"Could not write transcript: {exc}")

        return WatchActionOutcome.done(
            f"Transcribed {path.name} to {target.name}", result_path=target
        )


__all__ = [
    "OUTCOME_DONE",
    "OUTCOME_FAILED",
    "OUTCOME_SKIPPED",
    "AiAction",
    "CloudTranscribeAction",
    "ConvertAction",
    "CopyAction",
    "MoveAction",
    "OcrAction",
    "OpenAction",
    "RunMacroAction",
    "RunPythonTransformAction",
    "UnavailableAction",
    "WatchAction",
    "WatchActionOutcome",
    "WatchActionRegistry",
    "WatchItem",
    "default_registry",
]
