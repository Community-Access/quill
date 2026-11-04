"""Do a Project Task: the runner the task window drives (code.md 4.9) -- wx-free.

The same shape as :class:`~quill.core.ai.document_task.DocumentTaskRunner`
(``start``, ``finish``, ``send``, ``end``, ``cancel``, an ``emit`` attribute), so
the shared agent window drives it unchanged; one runner lives for the whole
task, across turns.

**One turn, inside** (code.md 4.9):

1. The person presses Enter. :meth:`start` builds this turn's tools and a
   session on the UI thread and does nothing slow.
2. The engine plans (``project.plan``; the window says "The plan is ready"),
   reads without questions, and proposes edits into the turn's change set.
3. When it wants to run a command, or the turn ends with edits pending, the
   turn pauses for **review**. Accepted changes are written together, after
   the checkpoint is safe; the engine is told exactly what was accepted.
4. A command, once approved (or on the person's own allow list), runs in its
   process tree; its result sentence is spoken and its output becomes a
   document.
5. When the session ends, :meth:`finish` reviews anything still pending,
   closes the checkpoint and builds the closing sentence from what actually
   happened, never from the model's claims.

**Each turn is its own engine session.** The next turn is told what happened
earlier (instruction, plan, changes, command results) rather than relying on
an engine's memory, so a turn boundary is always exact: the review, the
checkpoint and the summary happen at a moment QUILL knows about, the same
under every engine.

**Coach mode** (code.md 5.9) keeps only reading and pointing; **Explain This
Turn** is a coach-mode turn about the last one. A step cap stops a runaway
turn: "The task stopped after 40 steps."
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Protocol

from quill.core.ai import project_task_words as words
from quill.core.ai.activity_log import ActivityLog
from quill.core.ai.approvals import Approver
from quill.core.ai.change_set import ChangeSet
from quill.core.ai.checkpoints import CheckpointStore, UndoReport
from quill.core.ai.command_runner import (
    KEPT_FOR_PERSON,
    AllowList,
    CommandAssessment,
    CommandRunner,
    assess_command,
)
from quill.core.ai.context_builder import ContextScope
from quill.core.ai.document_task import DocumentTaskOutcome
from quill.core.ai.family_tools import FamilyTool, FamilyToolRegistry
from quill.core.ai.harness import AgentSpec, AIContext, HarnessResult, ToolHarness, ToolSession
from quill.core.ai.permissions import PermissionBroker, RiskLevel
from quill.core.ai.project import Project
from quill.core.ai.project_store import (
    find_instruction_files,
    instruction_choice,
    instructions_text,
    project_data_dir,
    set_instruction_choice,
)
from quill.core.ai.project_tools import PROJECT_APP, project_tools
from quill.core.ai.project_transcript import TurnLog, render_markdown
from quill.core.ai.test_summary import summarize_output, trim_for_model
from quill.core.ai.tool_gateway import AgentIdentity, Emit

__all__ = ["MAX_STEPS", "ProjectTaskRunner", "ProjectTaskUi", "default_project_agent"]

#: Tool calls in one turn before the person is asked whether to go on.
MAX_STEPS = 40


class ProjectTaskUi(Protocol):
    """What the runner asks of the window. Every call comes from a worker thread."""

    def review(self, changes: ChangeSet) -> bool: ...
    def approve_command(self, assessment: CommandAssessment, question: str) -> str: ...
    def keep_waiting(self, seconds: float) -> bool: ...
    def keep_going(self, steps: int) -> bool: ...
    def plan_ready(self, steps: list[str]) -> None: ...
    def note(self, text: str) -> None: ...
    def command_done(self, sentence: str, output: Path, ok: bool) -> None: ...
    def files_changed(self, paths: list[Path]) -> None: ...


def default_project_agent() -> AgentSpec:
    return AgentSpec(
        id="project-task",
        display_name="Project task",
        system_prompt="",
        description="Carries out a task across the files of a project folder.",
        risk=RiskLevel.MEDIUM,
        default_scope=ContextScope.PROMPT_ONLY,
        needs_tool_use=True,
    )


@dataclass
class ProjectTaskRunner:
    """One project task: its turns, its change set, its checkpoints and commands."""

    harness: ToolHarness
    approver: Approver
    project: Project
    ui: ProjectTaskUi
    data_dir: Path
    broker: PermissionBroker = field(default_factory=PermissionBroker)
    activity: ActivityLog = field(default_factory=ActivityLog)
    agent: AgentSpec = field(default_factory=default_project_agent)
    emit: Emit = field(default=lambda _event: None)
    coach: bool = False
    #: ``() -> str``: the git branch and changed files, or "" when not git.
    git_reader: Callable[[], str] | None = None
    on_usage: Callable[..., None] | None = None
    keep_open: bool = False
    turns: list[TurnLog] = field(default_factory=list, init=False)
    changes: ChangeSet = field(default_factory=ChangeSet, init=False)
    _session: ToolSession | None = field(default=None, init=False, repr=False)
    _registry: FamilyToolRegistry | None = field(default=None, init=False, repr=False)
    _steps: int = field(default=0, init=False, repr=False)
    _last_output: Path | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        folder = project_data_dir(self.data_dir, self.project)
        self.checkpoints = CheckpointStore(self.project, self.data_dir)
        self.allow_list = AllowList(self.data_dir, self.project.key)
        self.commands = CommandRunner(
            root=self.project.root,
            output_dir=folder / "output",
            keep_waiting=lambda seconds: self.ui.keep_waiting(seconds),
        )
        self.history_path = folder / "task-history.md"

    # -- what the window reads ---------------------------------------------- #

    @property
    def registry(self) -> FamilyToolRegistry | None:
        return self._registry

    @property
    def current_turn(self) -> TurnLog | None:
        return self.turns[-1] if self.turns else None

    @property
    def last_output(self) -> Path | None:
        return self._last_output

    def transcript_markdown(self) -> str:
        return render_markdown(self.project.name, self.turns)

    def instruction_files_to_ask(self) -> list[str]:
        """The project's agent notes, when the person has not yet said whether to use them."""
        if instruction_choice(self.data_dir, self.project):
            return []
        return find_instruction_files(self.project)

    def choose_instructions(self, use: bool) -> None:
        set_instruction_choice(self.data_dir, self.project, use)

    # -- a turn ------------------------------------------------------------- #

    def start(
        self,
        instruction: str,
        context_text: str = "",
        *,
        coach: bool | None = None,
        tools: list[FamilyTool] | None = None,
    ) -> ToolSession:
        """Build this turn's tools and session. Does not launch anything."""
        coaching = self.coach if coach is None else coach
        turn = TurnLog(number=len(self.turns) + 1, instruction=instruction, coach=coaching)
        self.turns.append(turn)
        self._steps = 0
        identity = AgentIdentity(self.agent.id, self.agent.risk, harness=self.harness.id)
        registry = FamilyToolRegistry(
            self.broker, self.activity, identity, self.emit, app_scope=PROJECT_APP
        )
        chosen = tools if tools is not None else project_tools(self, coach=coaching)
        registry.register_app(PROJECT_APP, [self._counted(t) for t in chosen])
        self._grant_vendor_tools(registry, turn, coaching)
        extra = words.COACH_INSTRUCTIONS if coaching else ""
        spec = replace(
            self.agent,
            system_prompt="\n\n".join(
                part
                for part in (
                    self.agent.system_prompt.strip(),
                    words.PROJECT_TASK_INSTRUCTIONS,
                    extra,
                )
                if part
            ),
        )
        ctx = AIContext(prompt=instruction, context_text=context_text or self._context())
        session = self.harness.start_tool_session(
            spec,
            ctx,
            registry,
            self.approver,
            self.emit,
            keep_open=self.keep_open,
            on_usage=self.on_usage,
        )
        self._registry = registry
        self._session = session
        return session

    def explain_last_turn(self) -> ToolSession | None:
        """Explain This Turn: a coach-mode turn about the one before (code.md 5.9)."""
        if not self.turns:
            return None
        return self.start(words.EXPLAIN_INSTRUCTION, coach=True)

    def finish(self, result: HarnessResult) -> DocumentTaskOutcome:
        """End the turn: review what is pending, close the checkpoint, sum it up."""
        turn = self.current_turn
        if turn is None:
            return DocumentTaskOutcome(status=result.status, summary="No task was started.")
        if self.changes.pending and result.status != "error":
            self._review_pending()
        self.checkpoints.close_turn()
        summary = words.turn_summary(
            turn.number,
            status=result.status,
            written=turn.written,
            created=turn.created,
            deleted=turn.deleted,
            rejected=turn.rejected,
            commands=words.commands_sentence(turn.commands),
        )
        turn.result = summary
        turn.answer = result.final_text.strip()
        self._save_history()
        changed = (*turn.written, *turn.created, *turn.deleted)
        return DocumentTaskOutcome(
            status=result.status,
            summary=summary,
            answer=turn.answer,
            changes=tuple(changed),
            declined=turn.rejected,
            error=result.error,
        )

    def send(self, follow_up: str) -> None:
        if self._session is not None:
            self._session.send(follow_up)

    def end(self) -> None:
        if self._session is not None:
            self._session.end()

    def cancel(self) -> None:
        """Stop: the session, and the running command with its whole tree."""
        self.commands.stop()
        if self._session is not None:
            self._session.cancel()

    def undo_last_turn(self) -> UndoReport:
        report = self.checkpoints.undo_last()
        if report.ok:
            self.ui.files_changed([
                self.project.root / p for p in (*report.restored, *report.removed)
            ])
            if self.turns:
                self.turns[-1].result += f" {report.sentence}"
                self._save_history()
        return report

    # -- the tools' host (ProjectToolHost) ----------------------------------- #

    def record_plan(self, steps: list[str]) -> str:
        turn = self.current_turn
        if turn is None or not steps:
            return "Give the plan as a list of steps."
        turn.plan = steps
        self.ui.plan_ready(steps)
        return "The plan is recorded and shown to the person. Carry on."

    def ask_person(self, question: str) -> str:
        if self.current_turn is not None and question.strip():
            self.current_turn.questions.append(question.strip())
        self.ui.note(f"Question for you: {question.strip()}")
        return "The question is shown to the person. End your turn now; their answer comes next."

    def point_to(self, path: str, line: int, note: str) -> str:
        where = f"{path} line {line}"
        if self.current_turn is not None:
            self.current_turn.pointers.append(f"{where}: {note}")
        self.ui.note(f"Look at {where}: {note}")
        return "Shown to the person."

    def note(self, text: str) -> None:
        self.ui.note(text)

    def git_status(self) -> str:
        reader = self.git_reader
        if reader is None:
            return "This project does not use git, or git is not available."
        try:
            return str(reader()) or "No changes."
        except Exception as error:  # noqa: BLE001 - a git failure is text for the model
            return f"git status could not run: {error}"

    def run_command(self, command: str, reason: str) -> str:
        assessment = assess_command(command, self.project.root)
        if not assessment.command:
            return "Give the command to run."
        if not assessment.runnable:
            self.ui.note(
                f"Not run, kept for you: {assessment.command} ({assessment.kept_for_person})."
            )
            return KEPT_FOR_PERSON
        reviewed = self._review_pending()
        if self.allow_list.bypass:
            # Decision 7's deliberate bypass: never silent, always in the record.
            self.ui.note(words.bypass_note(assessment.command))
        elif not self.allow_list.allows(assessment):
            question = words.command_question(assessment.command, reason, self.project.name)
            choice = self.ui.approve_command(assessment, question)
            if choice == "deny":
                self.ui.note(f"Not run: {assessment.command}.")
                return f"{reviewed} The person did not allow this command.".strip()
            if choice == "always" and assessment.may_always_allow:
                self.allow_list.add(assessment.command)
        self.checkpoints.ensure_turn()
        result = self.commands.run(assessment.command)
        self.checkpoints.record_after()
        self._last_output = result.output_path
        output = result.output()
        if result.could_not_start:
            sentence = f"The command could not start: {result.could_not_start}"
        elif result.stopped:
            sentence = "The command was stopped."
        else:
            sentence = summarize_output(output, result.exit_code, assessment.command)
        if self.current_turn is not None:
            self.current_turn.commands.append(f"{assessment.command}: {sentence}")
        ok = result.exit_code == 0 and not result.stopped and not result.could_not_start
        self.ui.command_done(sentence, result.output_path, ok)
        text = trim_for_model(output, sentence)
        if result.exit_code not in (0, None):
            text += "\nBefore you try a fix, say in one plain sentence what this error means."
        return f"{reviewed}\n{text}".strip()

    # -- inside ---------------------------------------------------------------- #

    def _grant_vendor_tools(self, registry: FamilyToolRegistry, turn: TurnLog, coach: bool) -> None:
        """Decision 4: the engine's own tools this project allows, never in coach mode."""
        from quill.core.ai.vendor_tools import (
            VendorToolChoices,
            engine_for_harness,
            permission_kinds,
            vendor_tools_sentence,
        )

        engine = engine_for_harness(self.harness.id)
        if coach or not engine:
            return
        enabled = VendorToolChoices(self.data_dir, self.project.key).enabled(engine)
        if not enabled:
            return
        registry.vendor_tools = enabled
        registry.vendor_kinds = permission_kinds(engine, enabled)
        registry.vendor_cwd = str(self.project.root)
        turn.engine_tools = vendor_tools_sentence(engine, enabled)
        self.ui.note(turn.engine_tools)
        # Their writes skip review, so the checkpoint is taken before the turn.
        self.checkpoints.ensure_turn()

    def _counted(self, tool: FamilyTool) -> FamilyTool:
        inner = tool.handler

        def handler(args: dict[str, Any]) -> Any:
            self._steps += 1
            if self._steps == MAX_STEPS + 1 and not self.ui.keep_going(MAX_STEPS):
                self.cancel()
                return "The person stopped the task here. End your turn."
            return inner(args)

        return replace(tool, handler=handler)

    def _review_pending(self) -> str:
        """Show pending changes for review; write what was accepted. Text for the model."""
        if not self.changes.pending:
            return ""
        if not self.ui.review(self.changes):
            self.changes.reject_all()
        outcome = self.changes.outcome_text()
        turn = self.current_turn
        rejected = sum(f.change_count - f.accepted_count for f in self.changes.files)
        lines = [f.row_text() for f in self.changes.files]
        if not any(f.accepted_count for f in self.changes.files):
            self.changes.clear()
            if turn is not None:
                turn.rejected += rejected
                turn.changes.extend(lines)
            return outcome
        self.checkpoints.ensure_turn()
        report = self.changes.apply(self.project.resolve)
        if not report.ok:
            self.ui.note(report.error)
            self.changes.clear()
            return f"{outcome} But writing failed, so nothing changed: {report.error}"
        self.checkpoints.record_after()
        if turn is not None:
            turn.rejected += rejected
            turn.changes.extend(lines)
            turn.written.extend(p for p in report.written if p not in turn.written)
            turn.created.extend(p for p in report.created if p not in turn.created)
            turn.deleted.extend(p for p in report.deleted if p not in turn.deleted)
        self.ui.files_changed([self.project.root / p for p in report.touched])
        return outcome

    def _context(self) -> str:
        parts = [f"Project: {self.project.name}, at {self.project.root}."]
        if self.git_reader is not None:
            try:
                branch = self.git_reader().splitlines()[0]
                parts.append(branch)
            except Exception:  # noqa: BLE001 - git is a help, never a blocker
                pass
        if instruction_choice(self.data_dir, self.project) == "yes":
            notes = instructions_text(self.project, find_instruction_files(self.project))
            if notes:
                parts.append(notes)
        earlier = [line for turn in self.turns[:-1] for line in turn.context_lines()]
        if earlier:
            text = "\n".join(earlier)
            parts.append("Earlier in this task:\n" + text[-8000:])
        return "\n\n".join(parts)

    def save_history(self) -> None:
        """Write the headed transcript to the project's task history in app data."""
        self._save_history()

    def _save_history(self) -> None:
        from quill.core.ai.change_set import write_text_atomic

        try:
            write_text_atomic(self.history_path, self.transcript_markdown())
        except OSError:
            pass
