"""The assistant applies small-local-model quality shaping only where it should (#1319)."""

from __future__ import annotations

from quill.core.ai.assistant import Assistant


class _ScriptedBackend:
    """Fake backend returning queued responses and recording every prompt."""

    def __init__(self, responses: list[str], *, is_local: bool) -> None:
        self._responses = list(responses)
        self.is_local = is_local
        self.prompts: list[str] = []

    def is_available(self):  # noqa: ANN201 - protocol shape
        return True, None

    def respond(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self._responses.pop(0) if self._responses else "fallback"

    def respond_stream(self, prompt: str, on_delta) -> str:  # noqa: ANN001
        result = self.respond(prompt)
        on_delta(result)
        return result


def test_local_generative_op_adds_negative_examples_and_retries_on_hedging() -> None:
    backend = _ScriptedBackend(["Clearly, it seems fine.", "It is fine."], is_local=True)
    assistant = Assistant(backend=backend)

    result = assistant.transform("rewrite", "some text")

    assert result == "It is fine."  # the retried, cleaned answer wins
    assert len(backend.prompts) == 2  # first attempt + one retry
    assert "Weak:" in backend.prompts[0]  # negative examples prepended
    assert "Revise your previous answer" in backend.prompts[1]  # named-word retry


def test_local_generative_op_does_not_retry_on_clean_output() -> None:
    backend = _ScriptedBackend(["A crisp, direct rewrite."], is_local=True)
    assistant = Assistant(backend=backend)

    result = assistant.transform("rewrite", "some text")

    assert result == "A crisp, direct rewrite."
    assert len(backend.prompts) == 1  # clean output -> no retry


def test_cloud_backend_gets_no_shaping_even_when_output_hedges() -> None:
    backend = _ScriptedBackend(["Clearly, it seems fine."], is_local=False)
    assistant = Assistant(backend=backend)

    result = assistant.transform("rewrite", "some text")

    assert result == "Clearly, it seems fine."  # not retried
    assert len(backend.prompts) == 1
    assert "Weak:" not in backend.prompts[0]  # no negative-example block for cloud


def test_faithful_transform_is_never_reshaped_on_a_local_backend() -> None:
    # fix_grammar must preserve the source; a hedge in the corrected text must
    # not trigger a rewrite that could change meaning.
    backend = _ScriptedBackend(["It seems the cat sat."], is_local=True)
    assistant = Assistant(backend=backend)

    result = assistant.transform("fix_grammar", "it seem the cat sat")

    assert result == "It seems the cat sat."
    assert len(backend.prompts) == 1
    assert "Weak:" not in backend.prompts[0]
