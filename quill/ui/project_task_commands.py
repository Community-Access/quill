"""Project tasks, shared by QUILL and QUILL Lite (code.md 2.1, 4.8, 6.3, 6.4).

A base of :class:`quill.ui.hosted_ai_commands.HostedAiMixin`, like Do a
Document Task, so both editors get every handler from one place and QUILL's
adapter keeps having no commands of its own (rule 10). Every command is the
Developer profile's: in QUILL it needs ``core.developer``, in QUILL Lite the
Coding area, and the host's ``feature_enabled("coding")`` answers for both.

- **Open Project Folder** makes a folder the project, for every window of the
  editor. **Close Project** puts Ctrl+3 back to Do a Document Task.
- **Ctrl+3** opens Do a Project Task when a project is open, and Do a
  Document Task when none is: one key, one window, and the status line says
  which.
- **Stop Agent** stops the running task from any window, the command it runs
  included, without finding the task window first (4.8).
- **Undo Last Agent Turn** works even after the task window is closed, and
  after QUILL restarts: the checkpoints are on disk.
- **Open Command Output**, **Open Task Transcript**, **Explain Last Turn**,
  **Commands Allowed in This Project** and **Engine Tools for This Project**
  reach the window's own buttons from the menus.

Safe Mode refuses project tasks, as it refuses the engines.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from quill.core.ai import project_task_words as words
from quill.ui.hosted_ai_task_commands import AgentTaskMixin

__all__ = ["ProjectTaskMixin"]

#: The host's feature name for the Developer profile's coding features.
CODING_FEATURE = "coding"


class ProjectTaskMixin(AgentTaskMixin):
    """The project commands, over Do a Document Task, and the project window's editor half."""

    # -- state, kept on the host so every window of the editor shares it ------- #

    def _ai_project(self) -> Any:
        return getattr(self._ai_host(), "ai_project", None)  # type: ignore[attr-defined]

    def _ai_project_window(self) -> Any:
        window = getattr(self._ai_host(), "ai_project_window", None)  # type: ignore[attr-defined]
        return window if window else None

    def _developer_on(self) -> bool:
        host = self._ai_host()  # type: ignore[attr-defined]
        check = getattr(host, "feature_enabled", None)
        return bool(callable(check) and check(CODING_FEATURE))

    def _developer_ready(self) -> bool:
        """The Developer profile is on and Safe Mode is off; says why not, once."""
        if not self._developer_on():
            self._announce(words.NEEDS_DEVELOPER)  # type: ignore[attr-defined]
            return False
        if self._ai_safe_mode():  # type: ignore[attr-defined]
            from quill.core.ai.connection_words import SAFE_MODE_ABOUT

            self._announce(SAFE_MODE_ABOUT)  # type: ignore[attr-defined]
            return False
        return True

    def _project_data_dir(self) -> Path:
        return Path(self._ai_host().data_dir)  # type: ignore[attr-defined]

    # -- the commands ------------------------------------------------------------ #

    def cmd_ai_task(self) -> None:
        """Ctrl+3: a project task when a project is open, else a document task."""
        if self._ai_project() is not None and self._developer_on():
            self.cmd_project_task()
            return
        super().cmd_ai_task()  # type: ignore[misc]

    def cmd_open_project_folder(self) -> None:
        if not self._developer_ready():
            return
        from quill.core.ai.project import Project, ProjectError
        from quill.core.ai.project_store import RecentProjects, git_status_text
        from quill.ui.project_open_dialog import choose_project_folder

        recent = RecentProjects(self._project_data_dir())
        folder = choose_project_folder(self._ai_parent(), recent.existing())  # type: ignore[attr-defined]
        if folder is None:
            return
        try:
            project = Project(folder)
        except ProjectError as error:
            self._announce(str(error).split("] ", 1)[-1])  # type: ignore[attr-defined]
            return
        running = self._ai_project_window()
        if running is not None and getattr(running, "_running", False):
            self._announce(words.STOP_FIRST)  # type: ignore[attr-defined]
            return
        if running is not None:
            running.Close()
        host = self._ai_host()  # type: ignore[attr-defined]
        host.ai_project = project
        host.ai_project_window = None
        recent.add(project.root)
        branch = git_status_text(project.root).split("\n", 1)[0]
        branch = branch.removeprefix("Branch ").rstrip(".")
        self._ai_project_changed()
        self._announce(words.project_opened(project.name, branch))  # type: ignore[attr-defined]

    def cmd_close_project(self) -> None:
        if self._ai_project() is None:
            self._announce(words.NO_PROJECT)  # type: ignore[attr-defined]
            return
        window = self._ai_project_window()
        if window is not None and getattr(window, "_running", False):
            self._announce(words.STOP_FIRST)  # type: ignore[attr-defined]
            return
        if window is not None:
            window.Close()
        host = self._ai_host()  # type: ignore[attr-defined]
        host.ai_project = None
        host.ai_project_window = None
        self._ai_project_changed()
        self._announce(words.PROJECT_CLOSED)  # type: ignore[attr-defined]

    def cmd_project_task(self) -> None:
        self._open_project_task()

    def cmd_explain_agent_turn(self) -> None:
        window = self._ai_project_window()
        if window is not None:
            from quill.ui.hosted_ai_dialogs import take_focus

            take_focus(window)
            window.explain_last_turn()
            return
        self._announce(words.NOTHING_TO_EXPLAIN)  # type: ignore[attr-defined]

    def cmd_stop_agent(self) -> None:
        """Stop Agent, from anywhere: the project task, or a document task."""
        stopped = False
        window = self._ai_project_window()
        if window is not None and getattr(window, "_running", False):
            window.stop()
            stopped = True
        for other in (getattr(self, "_ai_windows", None) or {}).values():
            if other and getattr(other, "_running", False) and hasattr(other, "stop"):
                other.stop()
                stopped = True
        if not stopped:
            self._announce(words.NO_TASK_RUNNING)  # type: ignore[attr-defined]

    def cmd_undo_agent_turn(self) -> None:
        project = self._ai_project()
        if project is None:
            self._announce(words.NO_PROJECT)  # type: ignore[attr-defined]
            return
        window = self._ai_project_window()
        if window is not None:
            window.undo_last_turn()
            return
        from quill.core.ai.checkpoints import CheckpointStore

        report = CheckpointStore(project, self._project_data_dir()).undo_last()
        if report.ok:
            self._ai_reload_changed([project.root / p for p in (*report.restored, *report.removed)])
        if report.edited_since:
            self._offer_undo_comparison(project, report)
            return
        self._announce(report.sentence)  # type: ignore[attr-defined]

    def _offer_undo_comparison(self, project: Any, report: Any) -> None:
        """Undo was refused to keep the person's edits: offer the file as it was (4.5).

        Yes opens the first edited file's text from before the agent's turn, as
        a document beside the person's own, so they can compare and decide.
        """
        import wx

        from quill.core.ai.change_set import write_text_atomic
        from quill.core.ai.checkpoints import CheckpointStore
        from quill.core.ai.project_store import project_data_dir
        from quill.ui.dialog_contract import show_message_box

        answer = show_message_box(
            words.undo_compare_question(report.sentence),
            words.UNDO_REFUSED_TITLE,
            wx.YES_NO | wx.ICON_QUESTION,
            self._ai_parent(),  # type: ignore[attr-defined]
        )
        if answer != wx.YES:
            return
        store = CheckpointStore(project, self._project_data_dir())
        turn = store.last_turn()
        rel = report.edited_since[0]
        if turn is None:
            return
        name = Path(rel).name
        copy = (
            project_data_dir(self._project_data_dir(), project)
            / "before"
            / (f"{name} before turn {turn.number}{Path(rel).suffix or '.txt'}")
        )
        write_text_atomic(copy, store.before_text(turn, rel))
        self._ai_open_file(copy)

    def cmd_open_command_output(self) -> None:
        window = self._ai_project_window()
        if window is not None and getattr(window._runner, "last_output", None) is not None:
            window.open_output()
            return
        project = self._ai_project()
        if project is None:
            self._announce(words.NO_PROJECT)  # type: ignore[attr-defined]
            return
        from quill.core.ai.project_store import project_data_dir

        folder = project_data_dir(self._project_data_dir(), project) / "output"
        outputs = sorted(folder.glob("command-*.txt")) if folder.is_dir() else []
        if not outputs:
            self._announce(words.NO_OUTPUT)  # type: ignore[attr-defined]
            return
        self._ai_open_file(max(outputs, key=lambda p: p.stat().st_mtime))

    def cmd_project_transcript(self) -> None:
        window = self._ai_project_window()
        if window is not None and getattr(window._runner, "turns", None):
            window.open_transcript()
            return
        project = self._ai_project()
        if project is None:
            self._announce(words.NO_PROJECT)  # type: ignore[attr-defined]
            return
        from quill.core.ai.project_store import project_data_dir

        history = project_data_dir(self._project_data_dir(), project) / "task-history.md"
        if not history.is_file():
            self._announce(words.NO_TRANSCRIPT_YET)  # type: ignore[attr-defined]
            return
        self._ai_open_file(history)

    def cmd_project_allowed_commands(self) -> None:
        project = self._ai_project()
        if project is None:
            self._announce(words.NO_PROJECT)  # type: ignore[attr-defined]
            return
        from quill.core.ai.command_runner import AllowList
        from quill.ui.project_command_dialog import edit_allowed_commands

        edit_allowed_commands(
            self._ai_parent(),  # type: ignore[attr-defined]
            AllowList(self._project_data_dir(), project.key),
            project.name,
        )

    def cmd_project_engine_tools(self) -> None:
        project = self._ai_project()
        if project is None:
            self._announce(words.NO_PROJECT)  # type: ignore[attr-defined]
            return
        from quill.core.ai.agent_task_words import engine_name
        from quill.core.ai.vendor_tools import VendorToolChoices, engine_for_harness
        from quill.ui.project_open_dialog import edit_engine_tools

        service = self._ai_service()  # type: ignore[attr-defined]
        connection = str(getattr(service, "connection_in_use", "") or "")
        engine = engine_for_harness(connection)
        edit_engine_tools(
            self._ai_parent(),  # type: ignore[attr-defined]
            engine,
            engine_name(connection),
            VendorToolChoices(self._project_data_dir(), project.key),
            self._announce,  # type: ignore[attr-defined]
        )

    # -- the window ------------------------------------------------------------- #

    def _open_project_task(self, *, explain: bool = False) -> None:
        if not self._developer_ready():
            return
        project = self._ai_project()
        if project is None:
            self._announce(words.NO_PROJECT)  # type: ignore[attr-defined]
            return
        existing = self._ai_project_window()
        if existing is not None:
            from quill.ui.hosted_ai_dialogs import take_focus

            take_focus(existing)
            return
        engine = self._ai_task_engine()  # type: ignore[attr-defined]
        if engine is None:
            return
        connection, harness = engine
        if not self._ask_about_instruction_files(project):
            return
        from quill.ui.project_task_window import ProjectTaskHooks, ProjectTaskWindow

        hooks = ProjectTaskHooks(
            announce=self._announce,  # type: ignore[attr-defined]
            connection=connection,
            make_runner=lambda approver, ui: self._project_runner(harness, approver, ui, project),
            make_host=lambda _bridge, _note: None,
            open_file=self._ai_open_file,
            files_changed=self._ai_reload_changed,
            cue=self._ai_cue,
            project=project.name,
            explain_first=explain,
            edit_allowed=lambda _runner: self.cmd_project_allowed_commands(),
            edit_engine_tools=lambda _runner: self.cmd_project_engine_tools(),
            undo_refused=lambda report: self._offer_undo_comparison(project, report),
        )
        window = ProjectTaskWindow(self._ai_parent(), hooks)  # type: ignore[attr-defined]
        host = self._ai_host()  # type: ignore[attr-defined]
        host.ai_project_window = window

        def _forget(event: Any) -> None:
            if getattr(host, "ai_project_window", None) is window:
                host.ai_project_window = None
            event.Skip()

        import wx

        window.Bind(wx.EVT_CLOSE, _forget)
        window.Show()

    def _project_runner(self, harness: Any, approver: Any, ui: Any, project: Any) -> Any:
        from quill.core.ai.project_store import git_status_text
        from quill.core.ai.project_task import ProjectTaskRunner

        return ProjectTaskRunner(
            harness=harness,
            approver=approver,
            project=project,
            ui=ui,
            data_dir=self._project_data_dir(),
            git_reader=(lambda: git_status_text(project.root)) if project.is_git else None,
        )

    def _ask_about_instruction_files(self, project: Any) -> bool:
        """Ask once per project whether to use its agent notes (4.7). False: not now."""
        from quill.core.ai.project_store import (
            find_instruction_files,
            instruction_choice,
            instructions_text,
            set_instruction_choice,
        )

        data_dir = self._project_data_dir()
        if instruction_choice(data_dir, project):
            return True
        files = find_instruction_files(project)
        if not files:
            return True
        from quill.ui.project_open_dialog import ask_instruction_files

        answer = ask_instruction_files(
            self._ai_parent(),  # type: ignore[attr-defined]
            files,
            lambda: instructions_text(project, files),
        )
        if answer is None:
            return False
        set_instruction_choice(data_dir, project, answer)
        return True

    # -- the editor half; each editor may override ------------------------------- #

    def _ai_project_changed(self) -> None:
        """The project was opened or closed: titles and status cells may show it."""
        refresh = getattr(self, "_refresh_project_cell", None)
        if callable(refresh):
            refresh()

    def _ai_cue(self, event: str) -> None:
        play = getattr(self, "cue", None) or getattr(self, "_cue", None)
        if callable(play):
            try:
                play(event)
            except Exception:  # noqa: BLE001 - a missing sound is never worth a failure
                pass

    def _ai_open_file(self, path: Path) -> None:
        """Open *path* as a document: QUILL's ``open_file``, QUILL Lite's ``open_path``."""
        opener = getattr(self, "open_file", None)
        if callable(opener):
            opener(Path(path), record_recent=False)
            return
        open_path = getattr(self._ai_host(), "open_path", None)  # type: ignore[attr-defined]
        if callable(open_path):
            open_path(Path(path))

    def _ai_reload_changed(self, paths: list[Path]) -> None:
        """Files a turn changed: reload the open ones in place, cursor kept, and say so."""
        reload = getattr(self, "_reload_agent_changed", None)
        if callable(reload):
            reload(paths)
