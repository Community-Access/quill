"""My GitHub Copilot as a hosted-AI route, driven against a fake ``copilot`` SDK.

No network and no real SDK: a stand-in module goes into ``sys.modules`` so
:class:`~quill.core.ai.copilot_chat.CopilotChat` runs its real code -- the
lazy import, the pack's client options, the session options, ``session.on``,
``send_and_wait``, ``list_models`` and ``rpc.account.get_quota``.

The fake mirrors ``github-copilot-sdk`` 1.0.28 as read from its source:
keyword-only signatures, events with a ``type`` and typed ``data``
(``assistant.message_delta`` ``delta_content``, ``assistant.message``
``content``, ``assistant.usage``, ``session.error`` with ``status_code`` /
``error_type`` / ``message``), ``send_and_wait`` raising
``Exception("Session error: ...")`` after a ``session.error`` and
``RuntimeError("Session aborted ...")`` after ``abort()``, ``ModelInfo`` with
``capabilities.supports.vision`` and ``policy.state``, and
``AccountQuotaSnapshot`` fields. Every call runs on a worker thread, because
the facade refuses the main (UI) thread.
"""

from __future__ import annotations

import asyncio
import base64
import sys
import threading
import types
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar

import pytest

from quill.core.ai import connection_caps, copilot_auth, copilot_runtime, copilot_state
from quill.core.ai.connection_choice import (
    NOT_AVAILABLE_YET,
    NOT_FOR_ACCOUNT,
    NOT_SET_UP,
    SIGNED_IN,
    SIGNED_OUT_BY_GITHUB,
    ConnectionFacts,
    limit_sentence,
    not_for_account_sentence,
    not_ready_sentence,
    revoked_sentence,
    row_states,
)
from quill.core.ai.connection_usage import GITHUB_USAGE_URL, usage_rows, which_ai_sentence
from quill.core.ai.copilot_chat import (
    AUTO_MODEL,
    AUTO_MODEL_NAME,
    ChatTurn,
    CopilotChat,
    CopilotChatError,
    CopilotImage,
    CopilotLimitReached,
    CopilotNotForAccount,
    CopilotRefused,
    CopilotSignInEnded,
    classify_failure,
    conversation_prompt,
)
from quill.core.ai.copilot_quota import CopilotQuota, QuotaBucket, reset_words, usage_clause
from quill.core.ai.text_only import FAMILY_INSTRUCTION

# -- the fake SDK ------------------------------------------------------------------ #


@dataclass
class Event:
    type: str
    data: Any


@dataclass
class PermissionDecisionReject:
    kind: ClassVar[str] = "reject"
    feedback: str | None = None


@dataclass
class AccountGetQuotaRequest:
    git_hub_token: str | None = None
    selection_id: str | None = None


@dataclass
class Rec:
    clients: int = 0
    client_kwargs: dict[str, Any] = field(default_factory=dict)
    sessions: list[dict[str, Any]] = field(default_factory=list)
    sent: list[str] = field(default_factory=list)
    attachments: list[Any] = field(default_factory=list)
    calls: list[str] = field(default_factory=list)
    #: Events each send_and_wait emits before answering.
    script: list[Event] = field(default_factory=list)
    reply: str = "The answer."
    #: Emit deltas slowly and wait for abort (the Stop test).
    slow: bool = False
    raise_on_wait: BaseException | None = None
    models: list[Any] = field(default_factory=list)
    models_error: BaseException | None = None
    quota: Any = None


def _fake_sdk(rec: Rec) -> types.ModuleType:
    class CopilotSession:
        def __init__(self) -> None:
            self.listeners: list[Callable[[Any], None]] = []
            self.aborted = False

        async def __aenter__(self) -> CopilotSession:
            return self

        async def __aexit__(self, *exc: object) -> None:
            rec.calls.append("disconnect")

        def on(self, handler: Callable[[Any], None]) -> Callable[[], None]:
            self.listeners.append(handler)
            return lambda: self.listeners.remove(handler)

        def _emit(self, event: Event) -> None:
            for listener in list(self.listeners):
                listener(event)

        async def send_and_wait(
            self,
            prompt: str,
            *,
            attachments: list[dict[str, Any]] | None = None,
            timeout: float = 60.0,
        ) -> Any:
            rec.calls.append("send_and_wait")
            rec.sent.append(prompt)
            rec.attachments.append(attachments)
            if rec.slow:
                for word in ("one ", "two ", "three ", "four "):
                    if self.aborted:
                        raise RuntimeError("Session aborted before response completed")
                    self._emit(Event("assistant.message_delta", _Delta(word)))
                    await asyncio.sleep(0.05)
                await asyncio.sleep(0.3)
                if self.aborted:
                    raise RuntimeError("Session aborted before response completed")
            for event in rec.script:
                self._emit(event)
                if event.type == "session.error":
                    raise Exception(f"Session error: {event.data.message}")
            if rec.raise_on_wait is not None:
                raise rec.raise_on_wait
            return Event("assistant.message", _Message(rec.reply))

        async def abort(self) -> None:
            rec.calls.append("abort")
            self.aborted = True

    class Account:
        async def get_quota(self, params: AccountGetQuotaRequest) -> Any:
            assert isinstance(params, AccountGetQuotaRequest)
            rec.calls.append("get_quota")
            return rec.quota

    class CopilotClient:
        def __init__(
            self,
            *,
            connection: Any = None,
            env: dict[str, str] | None = None,
            github_token: str | None = None,
            use_logged_in_user: bool | None = None,
            working_directory: str | None = None,
            base_directory: str | None = None,
        ) -> None:
            rec.clients += 1
            rec.client_kwargs = {"github_token": github_token, "env": env}
            self.rpc = types.SimpleNamespace(account=Account())

        async def __aenter__(self) -> CopilotClient:
            return self

        async def __aexit__(self, *exc: object) -> None:
            rec.calls.append("stop")

        async def create_session(
            self,
            *,
            on_permission_request: Any = None,
            model: str | None = None,
            system_message: dict[str, str] | None = None,
            available_tools: list[str] | None = None,
            streaming: bool | None = None,
        ) -> CopilotSession:
            rec.sessions.append({
                "on_permission_request": on_permission_request,
                "model": model,
                "system_message": system_message,
                "available_tools": available_tools,
                "streaming": streaming,
            })
            return CopilotSession()

        async def list_models(self) -> list[Any]:
            rec.calls.append("list_models")
            if rec.models_error is not None:
                raise rec.models_error
            return list(rec.models)

    @dataclass
    class StdioRuntimeConnection:
        path: str | None = None

    class RuntimeConnection:
        @staticmethod
        def for_stdio(*, path: str | None = None, args: tuple[str, ...] = ()) -> Any:
            return StdioRuntimeConnection(path=path)

    module = types.ModuleType("copilot")
    module.CopilotClient = CopilotClient  # type: ignore[attr-defined]
    module.RuntimeConnection = RuntimeConnection  # type: ignore[attr-defined]
    return module


@dataclass
class _Delta:
    delta_content: str
    message_id: str = "m1"


@dataclass
class _Message:
    content: str


@dataclass
class _SessionError:
    error_type: str
    message: str
    status_code: int | None = None
    error_code: str | None = None
    remediation: str | None = None


@dataclass
class _Usage:
    model: str
    input_tokens: int
    output_tokens: int


class JsonRpcError(Exception):
    def __init__(self, code: int, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"JSON-RPC Error {code}: {message}")


def _model(model_id: str, name: str, *, vision: bool = False, state: str = "enabled") -> Any:
    supports = types.SimpleNamespace(vision=vision, reasoning_effort=False)
    return types.SimpleNamespace(
        id=model_id,
        name=name,
        capabilities=types.SimpleNamespace(supports=supports),
        policy=types.SimpleNamespace(state=state, terms=""),
        billing=None,
    )


def _snapshot(entitlement: int, used: int, reset: str = "2026-11-01T00:00:00Z") -> Any:
    return types.SimpleNamespace(
        entitlement_requests=entitlement,
        is_unlimited_entitlement=entitlement < 0,
        overage=0.0,
        overage_allowed_with_exhausted_quota=False,
        remaining_percentage=100.0,
        usage_allowed_with_exhausted_quota=False,
        used_requests=used,
        reset_date=reset,
    )


# -- fixtures ------------------------------------------------------------------- #


@pytest.fixture
def rec(monkeypatch: pytest.MonkeyPatch) -> Rec:
    recorder = Rec()
    module = _fake_sdk(recorder)
    rpc = types.ModuleType("copilot.rpc")
    rpc.PermissionDecisionReject = PermissionDecisionReject  # type: ignore[attr-defined]
    rpc.AccountGetQuotaRequest = AccountGetQuotaRequest  # type: ignore[attr-defined]
    module.rpc = rpc  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "copilot", module)
    monkeypatch.setitem(sys.modules, "copilot.rpc", rpc)
    for name in ("QUILL_SAFE_MODE", "COPILOT_CLI_PATH", "GH_TOKEN", "GITHUB_TOKEN"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(copilot_runtime, "find_copilot_cli", lambda: None)
    monkeypatch.setattr(copilot_auth, "stored_token", lambda name="QUILL": "gho_test")
    monkeypatch.setattr(copilot_auth, "forget_token", lambda name="QUILL": True)
    connection_caps.clear_model_capabilities()
    yield recorder
    connection_caps.clear_model_capabilities()


def _on_worker[T](fn: Callable[[], T]) -> T:
    """Run *fn* on a worker thread, as the app does, and return or raise its outcome."""
    box: dict[str, Any] = {}

    def target() -> None:
        try:
            box["value"] = fn()
        except BaseException as exc:  # noqa: BLE001 - re-raised on the test thread
            box["error"] = exc

    worker = threading.Thread(target=target)
    worker.start()
    worker.join(30)
    if "error" in box:
        raise box["error"]
    return box["value"]


def _chat(tmp_path: Path, **kwargs: Any) -> CopilotChat:
    return CopilotChat("QUILL Lite", app_name="QUILL Lite", data_dir=tmp_path, **kwargs)


# -- single requests -------------------------------------------------------------- #


def test_ask_sends_a_picture_as_a_blob_attachment(rec: Rec, tmp_path: Path) -> None:
    picture = CopilotImage(b"\x89PNG data", "image/png", "chart.png")
    answer = _on_worker(lambda: _chat(tmp_path).ask("What is this?", images=[picture]))
    assert answer.text == "The answer."
    assert rec.sent == ["What is this?"]
    assert rec.attachments == [
        [
            {
                "type": "blob",
                "data": base64.b64encode(b"\x89PNG data").decode("ascii"),
                "mimeType": "image/png",
                "displayName": "chart.png",
            }
        ]
    ]
    assert rec.calls == ["send_and_wait", "disconnect", "stop"]
    assert rec.client_kwargs["github_token"] == "gho_test"  # this app's own token
    assert "gho_test" not in (rec.client_kwargs["env"] or {}).values()


def test_session_offers_no_tools_and_appends_the_family_line(rec: Rec, tmp_path: Path) -> None:
    _on_worker(lambda: _chat(tmp_path).ask("Hi", system="Be brief."))
    session = rec.sessions[0]
    assert session["available_tools"] == ["quill_text_only"]
    assert session["system_message"]["mode"] == "append"
    content = session["system_message"]["content"]
    assert content.startswith("Be brief.") and content.endswith(FAMILY_INSTRUCTION)
    assert session["streaming"] is None and session["model"] is None
    decision = session["on_permission_request"](types.SimpleNamespace(kind="shell"), {})
    assert isinstance(decision, PermissionDecisionReject)


def test_chosen_model_is_passed_and_auto_lets_copilot_choose(rec: Rec, tmp_path: Path) -> None:
    _on_worker(lambda: _chat(tmp_path, model="gpt-6").ask("Hi"))
    _on_worker(lambda: _chat(tmp_path, model=AUTO_MODEL).ask("Hi"))
    assert rec.sessions[0]["model"] == "gpt-6"
    assert rec.sessions[1]["model"] is None


def test_a_picture_type_copilot_cannot_take_is_refused_before_anything_starts(
    rec: Rec, tmp_path: Path
) -> None:
    with pytest.raises(ValueError, match="image/bmp"):
        _on_worker(lambda: _chat(tmp_path).ask("x", images=[CopilotImage(b"BM", "image/bmp")]))
    assert rec.clients == 0


def test_usage_event_counts_tokens(rec: Rec, tmp_path: Path) -> None:
    rec.script = [Event("assistant.usage", _Usage("claude-sonnet", 120, 30))]
    answer = _on_worker(lambda: _chat(tmp_path).ask("Hi"))
    assert (answer.model, answer.input_tokens, answer.output_tokens) == ("claude-sonnet", 120, 30)


# -- conversations ------------------------------------------------------------------ #


def test_converse_resends_the_local_history_in_a_fresh_session(rec: Rec, tmp_path: Path) -> None:
    chat = _chat(tmp_path)
    history = [ChatTurn("user", "Name a colour."), ("assistant", "Blue.")]
    _on_worker(lambda: chat.converse(history, "Another?"))
    longer = [*history, ("user", "Another?"), ("assistant", "Red.")]
    _on_worker(lambda: chat.converse(longer, "Why?"))
    assert len(rec.sessions) == 2  # nothing kept server-side between turns
    first, second = rec.sent
    assert "User: Name a colour." in first and "Assistant: Blue." in first
    assert first.endswith("My next message:\nAnother?")
    assert "Assistant: Red." in second and second.endswith("Why?")
    assert conversation_prompt([], "Alone") == "Alone"


# -- streaming ------------------------------------------------------------------- #


def test_stream_delivers_each_piece_in_order(rec: Rec, tmp_path: Path) -> None:
    rec.script = [Event("assistant.message_delta", _Delta(p)) for p in ("Hel", "lo", ".")]
    rec.reply = "Hello."
    pieces: list[str] = []
    answer = _on_worker(lambda: _chat(tmp_path).stream("Hi", on_delta=pieces.append))
    assert pieces == ["Hel", "lo", "."]
    assert answer.text == "Hello." and not answer.stopped
    assert rec.sessions[0]["streaming"] is True


def test_stop_aborts_the_turn_and_keeps_the_text_so_far(rec: Rec, tmp_path: Path) -> None:
    rec.slow = True
    pieces: list[str] = []
    chat = _chat(tmp_path)
    chat.stop_poll_seconds = 0.01
    answer = _on_worker(
        lambda: chat.stream("Hi", on_delta=pieces.append, stop=lambda: len(pieces) >= 2)
    )
    assert answer.stopped
    assert "abort" in rec.calls
    assert answer.text.startswith("one two")


def test_a_timeout_aborts_and_is_worded(rec: Rec, tmp_path: Path) -> None:
    rec.raise_on_wait = TimeoutError("Timeout after 600s")
    with pytest.raises(CopilotChatError, match="took too long"):
        _on_worker(lambda: _chat(tmp_path).ask("Hi"))
    assert rec.calls[:2] == ["send_and_wait", "abort"]


# -- models ---------------------------------------------------------------------- #


def test_models_keep_the_service_order_and_record_vision(rec: Rec, tmp_path: Path) -> None:
    rec.models = [
        _model("claude-sonnet", "Claude Sonnet", vision=True),
        _model("gpt-mini", "GPT mini"),
        _model("o-pro", "O Pro", state="disabled"),
    ]
    listed = _on_worker(lambda: _chat(tmp_path).list_models())
    assert [m.id for m in listed.models] == ["claude-sonnet", "gpt-mini"]
    assert [m.vision for m in listed.models] == [True, False]
    assert not listed.auto_only
    seeing = connection_caps.record_for("copilot", model="claude-sonnet", available=True)
    blind = connection_caps.record_for("copilot", model="gpt-mini", available=True)
    assert connection_caps.can(seeing, connection_caps.PICTURES)
    assert not connection_caps.can(blind, connection_caps.PICTURES)
    assert "models.list" in blind.claim(connection_caps.PICTURES).source


@pytest.mark.parametrize("models", [[], [("auto", "Auto")]])
def test_copilot_free_lists_only_auto(rec: Rec, tmp_path: Path, models: list[Any]) -> None:
    rec.models = [_model(i, n) for i, n in models] + [_model("gpt-6", "GPT 6", state="disabled")]
    listed = _on_worker(lambda: _chat(tmp_path).list_models())
    assert listed.auto_only
    assert [(m.id, m.name) for m in listed.models] == [(AUTO_MODEL, AUTO_MODEL_NAME)]


# -- quota and the usage sentence ---------------------------------------------------- #


def test_quota_reads_githubs_count_into_the_usage_sentence(rec: Rec, tmp_path: Path) -> None:
    rec.quota = types.SimpleNamespace(
        quota_snapshots={"premium_interactions": _snapshot(300, 41), "chat": _snapshot(-1, 9)}
    )
    quota = _on_worker(lambda: _chat(tmp_path).quota())
    assert "get_quota" in rec.calls
    sentence = "My GitHub Copilot: 41 of 300 premium requests this month, by GitHub's count. "
    sentence += "Resets November 1."
    facts = ConnectionFacts(stored="copilot", copilot_available=True, copilot_signed_in=True)
    rows = {row.connection: row for row in usage_rows(facts, copilot_quota=quota)}
    assert rows["copilot"].sentence == sentence
    assert rows["copilot"].manage_url == GITHUB_USAGE_URL
    spoken = which_ai_sentence(facts, model="claude-sonnet", copilot_quota=quota)
    assert spoken.startswith("My GitHub Copilot, claude-sonnet. 41 of 300 premium requests")


def test_usage_clause_shapes() -> None:
    free = CopilotQuota({"premium_interactions": QuotaBucket(0, 0), "chat": QuotaBucket(50, 12)})
    assert usage_clause(free).startswith("12 of 50 chat requests this month")
    unlimited = CopilotQuota({"premium_interactions": QuotaBucket(-1, 3, reset_date="")})
    assert usage_clause(unlimited) == (
        "3 premium requests this month, no monthly limit, by GitHub's count."
    )
    assert usage_clause(None) == "GitHub's count is not read yet."
    assert reset_words("2026-12-01") == "December 1"
    assert reset_words("garbage") == ""


# -- the 10A.5 failures ------------------------------------------------------------- #


def test_a_401_ends_the_sign_in_and_forgets_the_token(
    rec: Rec, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    forgotten: list[str] = []
    monkeypatch.setattr(copilot_auth, "forget_token", lambda name="QUILL": forgotten.append(name))
    rec.script = [Event("session.error", _SessionError("authentication", "Bad token", 401))]
    with pytest.raises(CopilotSignInEnded) as caught:
        _on_worker(lambda: _chat(tmp_path).ask("Hi"))
    assert caught.value.sentence == revoked_sentence("copilot")
    assert forgotten == ["QUILL Lite"]
    assert copilot_state.load_marks("QUILL Lite", data_dir=tmp_path).ended_by_github


def test_a_spent_quota_is_the_limit_sentence(rec: Rec, tmp_path: Path) -> None:
    rec.script = [Event("session.error", _SessionError("quota_exceeded", "No quota left", 429))]
    with pytest.raises(CopilotLimitReached) as caught:
        _on_worker(lambda: _chat(tmp_path).ask("Hi"))
    assert caught.value.sentence == limit_sentence("copilot", "QUILL Lite")
    assert rec.calls.count("send_and_wait") == 1  # never retried


def test_copilot_off_for_the_account_reads_not_available(rec: Rec, tmp_path: Path) -> None:
    rec.models_error = JsonRpcError(-32603, "Copilot is disabled by your organization's policy")
    with pytest.raises(CopilotNotForAccount) as caught:
        _on_worker(lambda: _chat(tmp_path).list_models())
    assert caught.value.sentence == not_for_account_sentence()
    assert copilot_state.load_marks("QUILL Lite", data_dir=tmp_path).policy_off


def test_any_other_failure_is_worded_once(rec: Rec, tmp_path: Path) -> None:
    rec.raise_on_wait = RuntimeError("Session closed before response completed")
    with pytest.raises(CopilotChatError) as caught:
        _on_worker(lambda: _chat(tmp_path).ask("Hi"))
    assert type(caught.value) is CopilotChatError
    assert caught.value.sentence.startswith("GitHub Copilot did not answer: Session closed")


@pytest.mark.parametrize(
    ("kwargs", "outcome"),
    [
        ({"status_code": 401}, "revoked"),
        ({"remediation": "sign_in"}, "revoked"),
        ({"message": "Bad credentials"}, "revoked"),
        ({"status_code": 402}, "limit"),
        ({"error_code": "rate_limit_exceeded"}, "limit"),
        ({"status_code": 403}, "not_for_account"),
        ({"message": "You do not have access to Copilot"}, "not_for_account"),
        ({"message": "socket closed"}, "failed"),
    ],
)
def test_classify_failure(kwargs: dict[str, Any], outcome: str) -> None:
    assert classify_failure(**kwargs) == outcome


# -- readiness ------------------------------------------------------------------- #


@pytest.fixture
def parts(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> dict[str, Any]:
    state: dict[str, Any] = {"client_id": "Iv1.test", "cli": tmp_path / "copilot.exe"}
    state["sdk"] = True
    state["token"] = "gho_test"
    monkeypatch.setitem(copilot_auth.CLIENT_IDS, "QUILL Lite", "")
    monkeypatch.setattr(copilot_auth, "client_id", lambda name="QUILL": state["client_id"])
    monkeypatch.setattr(copilot_state, "resolve_cli_path", lambda: state["cli"])
    monkeypatch.setattr(copilot_state, "sdk_bundled", lambda: state["sdk"])
    monkeypatch.setattr(copilot_auth, "stored_token", lambda name="QUILL": state["token"])
    return state


def _copilot_row(tmp_path: Path, stored: str = "free") -> str:
    fields = copilot_state.connection_facts_fields("QUILL Lite", data_dir=tmp_path)
    facts = ConnectionFacts(stored=stored, **fields)
    return {row.connection: row.state for row in row_states(facts)}["copilot"]


def test_readiness_states(parts: dict[str, Any], tmp_path: Path) -> None:
    assert copilot_state.readiness("QUILL Lite", data_dir=tmp_path).ready
    assert _copilot_row(tmp_path) == SIGNED_IN
    parts["token"] = None
    assert _copilot_row(tmp_path) == NOT_SET_UP
    parts["client_id"] = ""
    assert _copilot_row(tmp_path) == NOT_AVAILABLE_YET
    parts["client_id"] = "Iv1.test"
    parts["cli"] = None  # no bundled CLI and no developer override
    assert _copilot_row(tmp_path) == NOT_AVAILABLE_YET
    parts["cli"] = tmp_path / "copilot.exe"
    parts["sdk"] = False
    assert _copilot_row(tmp_path) == NOT_AVAILABLE_YET


def test_marks_drive_the_row_and_a_new_sign_in_clears_the_ending(
    parts: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(copilot_auth, "forget_token", lambda name="QUILL": True)
    copilot_state.mark_ended_by_github("QUILL Lite", data_dir=tmp_path)
    parts["token"] = None
    assert _copilot_row(tmp_path, stored="copilot") == SIGNED_OUT_BY_GITHUB
    parts["token"] = "gho_new"
    assert _copilot_row(tmp_path) == SIGNED_IN
    copilot_state.mark_policy_off("QUILL Lite", data_dir=tmp_path)
    assert _copilot_row(tmp_path, stored="copilot") == NOT_FOR_ACCOUNT
    fields = copilot_state.connection_facts_fields("QUILL Lite", data_dir=tmp_path)
    assert not_ready_sentence(ConnectionFacts(stored="copilot", **fields)) == (
        not_for_account_sentence()
    )
    copilot_state.clear_marks("QUILL Lite", data_dir=tmp_path)
    assert _copilot_row(tmp_path) == SIGNED_IN


# -- refusals -------------------------------------------------------------------- #


def test_safe_mode_refuses_before_any_client(
    rec: Rec, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("QUILL_SAFE_MODE", "1")
    for call in (lambda c: c.ask("Hi"), lambda c: c.list_models(), lambda c: c.quota()):
        with pytest.raises(CopilotRefused, match="Safe Mode"):
            _on_worker(lambda call=call: call(_chat(tmp_path)))
    assert rec.clients == 0


def test_the_ui_thread_is_refused(rec: Rec, tmp_path: Path) -> None:
    assert threading.current_thread() is threading.main_thread()
    with pytest.raises(CopilotRefused, match="window's own thread"):
        _chat(tmp_path).ask("Hi")
    assert rec.clients == 0


def test_the_sdk_import_stays_lazy() -> None:
    source = Path(__file__).resolve().parents[4] / "quill" / "core" / "ai" / "copilot_chat.py"
    text = source.read_text(encoding="utf-8")
    assert "\nimport copilot" not in text and "\nfrom copilot" not in text
