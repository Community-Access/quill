"""The Copilot sign-in step, built for real with a fake device flow (codex.md 10A.3).

The old two-step "Set Up GitHub Copilot" dialog (install, then sign in) is
retired: the engine is bundled, so sign-in is the only step, and it is the one
sign-in step Choose Your AI uses for every connection, with GitHub's code in a
field of its own. The flow and the workers are replaced; the step is real.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
import wx

from quill.ui import copilot_onboarding_dialog as module


class _Flow:
    """Stands in for CopilotSignIn: a code at once, then the scripted outcome."""

    instances: list[_Flow] = []

    def __init__(self, agent: str, *, data_dir: Any = None) -> None:
        self.agent = agent
        self.data_dir = data_dir
        self.cancelled = False
        self.outcome: BaseException | None = None
        type(self).instances.append(self)

    def request_code(self) -> Any:
        return SimpleNamespace(
            user_code="WXYZ-9876", verification_uri="https://github.com/login/device"
        )

    def wait(self, _grant: Any) -> None:
        if self.outcome is not None:
            raise self.outcome

    def cancel(self) -> None:
        self.cancelled = True


@pytest.fixture
def step_world(wx_session_app, monkeypatch, wx_call_after, tmp_path: Path):
    import quill.core.ai.copilot_sign_in as core
    import quill.ui.update_download as download
    from quill.core.ai import copilot_auth

    _Flow.instances = []
    monkeypatch.setattr(core, "CopilotSignIn", _Flow)
    monkeypatch.setattr(copilot_auth, "is_configured", lambda agent="QUILL": True)
    token: dict[str, str | None] = {"value": None}
    monkeypatch.setattr(copilot_auth, "stored_token", lambda agent="QUILL": token["value"])
    copied: list[str] = []
    monkeypatch.setattr(module, "_copy", lambda text: copied.append(text) or True)
    jobs: list[tuple[str, Any, Any, Any]] = []

    def submit(name, work, *, on_success=None, on_failure=None):
        jobs.append((name, work, on_success, on_failure))

    monkeypatch.setattr(download, "thread_submit", submit)
    wx_call_after()

    def run_jobs() -> None:
        while jobs:
            name, work, on_success, on_failure = jobs.pop(0)
            try:
                result = work()
            except BaseException as error:  # noqa: BLE001 - as the worker would
                on_failure(name, error)
            else:
                on_success(name, result)

    return SimpleNamespace(jobs=jobs, run_jobs=run_jobs, copied=copied, token=token)


def _service(agent: str = "QUILL Lite") -> Any:
    return SimpleNamespace(agent_name=agent, data_dir=None)


def test_the_code_arrives_spaced_on_the_clipboard_and_said_once(step_world, monkeypatch) -> None:
    said: list[str] = []
    seen: dict[str, Any] = {}

    def show(step, title):
        step_world.run_jobs()  # the code, then the wait, as the workers would
        seen["title"] = title
        seen["sentence"] = step.status.GetValue()
        seen["code"] = step.code.GetValue()
        seen["default"] = step.open_button.IsEnabled()
        step_world.token["value"] = "gho_new"
        return wx.ID_OK  # the wait succeeded; the step closed itself

    monkeypatch.setattr("quill.ui.dialog_contract.show_modal_dialog", show)
    assert module.copilot_sign_in(None, _service(), said.append) is True

    assert seen["title"] == "Sign In to Your AI"
    assert seen["sentence"] == "To use My GitHub Copilot, approve QUILL Lite on GitHub's page."
    assert seen["code"].split() == ["W", "X", "Y", "Z", "d", "a", "s", "h", "9", "8", "7", "6"]
    assert step_world.copied == ["WXYZ-9876"]
    assert said == [f"The code is {seen['code']}. It is on the clipboard."]
    assert _Flow.instances[0].agent == "QUILL Lite"  # its own registration and token


def test_cancel_stops_the_wait_and_says_nothing(step_world, monkeypatch) -> None:
    said: list[str] = []
    monkeypatch.setattr(
        "quill.ui.dialog_contract.show_modal_dialog", lambda _step, _title: wx.ID_CANCEL
    )

    assert module.copilot_sign_in(None, _service(), said.append) is False
    assert _Flow.instances[0].cancelled is True
    assert said == []


def test_a_failed_wait_shows_its_sentence_in_the_step(step_world, monkeypatch) -> None:
    from quill.core.ai.copilot_sign_in import CopilotSignInFailed

    seen: dict[str, str] = {}

    def show(step, _title):
        _Flow.instances[0].outcome = CopilotSignInFailed("That code expired before it was used.")
        step_world.run_jobs()
        seen["status"] = step.status.GetValue()
        return wx.ID_CANCEL

    monkeypatch.setattr("quill.ui.dialog_contract.show_modal_dialog", show)
    assert module.copilot_sign_in(None, _service(), lambda _m: None) is False
    assert seen["status"] == "That code expired before it was used."


def test_no_registration_says_why_in_one_sentence_and_opens_nothing(
    step_world, monkeypatch
) -> None:
    from quill.core.ai import copilot_auth

    monkeypatch.setattr(copilot_auth, "is_configured", lambda agent="QUILL": False)
    shown: list[Any] = []
    monkeypatch.setattr(
        "quill.ui.dialog_contract.show_modal_dialog", lambda step, _t: shown.append(step)
    )
    said: list[str] = []

    assert module.copilot_sign_in(None, _service("QUILL"), said.append) is False
    assert shown == []
    assert said == [copilot_auth.sign_in_unavailable_message("QUILL")]


def test_the_install_step_is_gone_and_both_old_doors_open_this_step() -> None:
    body = Path("quill/ui/copilot_onboarding_dialog.py").read_text(encoding="utf-8")
    assert "install_pack" not in body
    assert "os.environ" not in body
    engines = Path("quill/ui/ai_hub_engines_panel.py").read_text(encoding="utf-8")
    actions = Path("quill/ui/main_frame_ai_actions.py").read_text(encoding="utf-8")
    assert "sign_in_copilot_for_app(" in engines
    assert "sign_in_copilot_for_app(" in actions
