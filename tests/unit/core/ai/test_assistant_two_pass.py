"""The assistant uses two-pass summarize only on a local backend, opt-in (#1320)."""

from __future__ import annotations

from quill.core.ai.assistant import Assistant


class _Backend:
    def __init__(self, *, is_local: bool) -> None:
        self.is_local = is_local
        self.prompts: list[str] = []

    def is_available(self):  # noqa: ANN201
        return True, None

    def respond(self, prompt: str) -> str:
        self.prompts.append(prompt)
        # Distinct replies so the caller's return value reveals which pass won.
        return f"reply-{len(self.prompts)}"

    def respond_stream(self, prompt: str, on_delta) -> str:  # noqa: ANN001
        return self.respond(prompt)


def test_local_summarize_runs_observe_then_rewrite() -> None:
    backend = _Backend(is_local=True)
    assistant = Assistant(backend=backend)
    assistant.summary_word_budget = 40

    result = assistant.transform("summarize", "The quarterly report covers three regions.")

    assert len(backend.prompts) == 2  # observe, then rewrite
    assert "The quarterly report" in backend.prompts[0]  # pass 1 sees the source
    assert "40 words" in backend.prompts[1]  # pass 2 carries the budget
    assert "The quarterly report" not in backend.prompts[1]  # pass 2 hides the source
    assert result == "reply-2"  # the rewrite's output is returned


def test_disabled_flag_falls_back_to_single_pass_on_local() -> None:
    backend = _Backend(is_local=True)
    assistant = Assistant(backend=backend)
    assistant.two_pass_summarize = False

    assistant.transform("summarize", "some source text")

    assert len(backend.prompts) == 1  # single pass


def test_cloud_backend_stays_single_pass() -> None:
    backend = _Backend(is_local=False)
    assistant = Assistant(backend=backend)

    assistant.transform("summarize", "some source text")

    assert len(backend.prompts) == 1  # cloud never pays for the second call


def test_non_summarize_op_is_never_two_pass() -> None:
    backend = _Backend(is_local=True)
    assistant = Assistant(backend=backend)

    assistant.transform("rewrite", "some source text")

    assert len(backend.prompts) == 1
