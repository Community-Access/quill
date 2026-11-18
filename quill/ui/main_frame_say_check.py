"""Help > Check What QUILL Says...: EdSharp's testSay, for QUILL's editor.

Runs each speak-only command once and twice with speech captured rather than
sent, then opens the report as a new document (see :mod:`quill.core.say_check`).
A command that would open a window is recorded as "opens <title>" and the
window is not shown, so the run never stops to wait for somebody.
"""

from __future__ import annotations

from typing import Any

from quill.core.say_check import SAY_CHECK_COMMANDS, SayCheckRow, say_check_report


class SayCheckMixin:
    """The editor frame's half of the Say check."""

    commands: Any
    _announce: Any
    _show_modal_dialog: Any

    def _register_say_check_commands(self) -> None:
        self.commands.register(
            "app.say_check",
            "Check What QUILL Says...",
            self.run_say_check,
            self._binding_for("app.say_check"),  # type: ignore[attr-defined]
        )

    def run_say_check(self) -> None:
        rows = self._say_check_rows()
        text = say_check_report(rows, reader=self._say_check_reader())
        opener = getattr(self, "_power_tools_open_text_in_new_buffer", None)
        if callable(opener):
            opener(text, f"Checked what QUILL says for {len(rows)} commands")
        else:
            self._announce(f"Checked what QUILL says for {len(rows)} commands")

    def _say_check_rows(self) -> list[SayCheckRow]:
        rows: list[SayCheckRow] = []
        said: list[str] = []
        real_announce, real_modal = self._announce, self._show_modal_dialog

        def capture(message: object = "", *_a: Any, **_k: Any) -> None:
            said.append(str(message))

        def no_window(_dialog: object, label: str = "", *_a: Any, **_k: Any) -> int:
            said.append(f"(opens the {label or 'a'} window)")
            return 5101  # wx.ID_CANCEL: the window answers Cancel

        self._announce = capture  # type: ignore[method-assign]
        self._show_modal_dialog = no_window  # type: ignore[method-assign]
        try:
            for command_id in SAY_CHECK_COMMANDS:
                command = self.commands.get(command_id)
                if command is None:
                    continue
                presses: list[tuple[str, ...]] = []
                for _press in (1, 2):
                    said.clear()
                    try:
                        self.commands.run(command_id)
                    except Exception as exc:  # noqa: BLE001 - a failing command is a finding
                        said.append(f"(failed: {exc})")
                    presses.append(tuple(said))
                # "Twice" is the second press straight after the first: what a
                # listener hears pressing it twice quickly.
                rows.append(
                    SayCheckRow(command.title, command.keybinding or "", presses[0], presses[1])
                )
        finally:
            self._announce = real_announce  # type: ignore[method-assign]
            self._show_modal_dialog = real_modal  # type: ignore[method-assign]
        return rows

    def _say_check_reader(self) -> str:
        try:
            from quill.platform.windows.sr_detect import detect_screen_reader

            found = detect_screen_reader()
            return found.name if found.detected else ""
        except Exception:  # noqa: BLE001 - naming the reader is a nicety
            return ""
