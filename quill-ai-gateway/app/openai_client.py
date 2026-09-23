"""The single call site that ever talks to OpenAI.

Everything upstream of this module (auth, quota, size limits, model selection)
has already run by the time :func:`complete` is called — this function's only
job is the HTTP call itself and turning the response into token counts. Keeping
this the *only* place ``OPENAI_API_KEY`` is read means an audit of "does this
key ever leak" has one call site to check.

Two things about the request body are load-bearing enough to have been split
into :func:`build_request_body`, which is a pure function so a test can assert
on it without a network call:

**Nothing but the allowlist is ever sent.** No ``tools``, no ``tool_choice``, no
``web_search_options``, no hosted file search, no attachments, no ``store``.
This is not a default to be overridden; it is the shape of the request. Web
search alone bills at $10 per thousand calls, which on this service's traffic
would cost sixteen times the entire model bill. ``tests/test_openai_request_shape.py``
fails the build if any key appears here that is not in :data:`ALLOWED_BODY_KEYS`.

**Output is capped by ``max_completion_tokens``, not ``max_tokens``.** Reasoning
models reject the older parameter outright, and the newer one is what bounds
reasoning and answer together — which is the same budget, and the reason
``app/routes/chat.py`` refuses to charge for a reply that spent it all on
thinking and returned nothing.
"""

from __future__ import annotations

from dataclasses import dataclass

import requests

__all__ = [
    "ALLOWED_BODY_KEYS",
    "Completion",
    "OpenAICallError",
    "build_request_body",
    "complete",
]

#: Every key that may appear in the JSON body sent upstream. Adding one is a
#: deliberate act with a test to update and a cost to justify.
ALLOWED_BODY_KEYS: frozenset[str] = frozenset({
    "model",
    "messages",
    "max_completion_tokens",
    "reasoning_effort",
})


class OpenAICallError(Exception):
    """The upstream call failed. Never includes the API key in its message —
    the key is never part of any exception text this module raises."""


@dataclass(frozen=True, slots=True)
class Completion:
    """One upstream reply, in the only terms the rest of the service needs.

    ``reasoning_tokens`` is included in ``tokens_out`` (the provider counts it
    there, and bills it there); it is broken out separately so the console can
    show how much of a bill went on thinking nobody ever saw.
    """

    text: str
    tokens_in: int
    tokens_out: int
    reasoning_tokens: int = 0

    @property
    def is_empty(self) -> bool:
        return not self.text.strip()

    @property
    def spent_everything_thinking(self) -> bool:
        """An empty reply that burned output tokens on reasoning.

        This is the failure the user experiences as "QUILL's AI is broken", and
        the one they must never be charged for.
        """
        return self.is_empty and self.reasoning_tokens > 0


def build_request_body(
    model_id: str, prompt: str, max_output_tokens: int, reasoning_effort: str | None
) -> dict:
    """The exact JSON body for one completion. Pure; no I/O.

    *reasoning_effort* of ``None`` omits the key entirely, which is what the
    retry path in :func:`complete` uses if a provider rejects the parameter.
    """
    body: dict = {
        "model": model_id,
        "messages": [{"role": "user", "content": prompt}],
        "max_completion_tokens": int(max_output_tokens),
    }
    if reasoning_effort is not None:
        body["reasoning_effort"] = reasoning_effort
    # Belt and braces: the allowlist is asserted in a test, but a body built at
    # runtime with an unexpected key would be a billed mistake, not a failed
    # test run.
    unexpected = set(body) - ALLOWED_BODY_KEYS
    if unexpected:  # pragma: no cover - unreachable unless this function changes
        raise OpenAICallError(f"Refusing to send unapproved request keys: {sorted(unexpected)}")
    return body


def _parse(payload: object) -> Completion:
    try:
        assert isinstance(payload, dict)
        text = payload["choices"][0]["message"]["content"] or ""
        usage = payload["usage"]
        tokens_in = int(usage["prompt_tokens"])
        tokens_out = int(usage["completion_tokens"])
    except (AssertionError, KeyError, IndexError, TypeError) as exc:
        raise OpenAICallError("OpenAI returned an unexpected response shape") from exc

    details = usage.get("completion_tokens_details") or {}
    try:
        reasoning = int(details.get("reasoning_tokens", 0) or 0)
    except (TypeError, ValueError):
        reasoning = 0

    return Completion(
        text=text, tokens_in=tokens_in, tokens_out=tokens_out, reasoning_tokens=reasoning
    )


def complete(
    app,
    model_id: str,
    prompt: str,
    max_output_tokens: int,
    reasoning_effort: str | None = "none",
) -> Completion:
    """Call the provider once and return the parsed :class:`Completion`.

    Token counts come from the provider's own ``usage`` block — never the
    client's, never our own estimate — because that is what the bill is
    computed from in :func:`app.limits.record_usage`.

    If the provider rejects ``reasoning_effort`` with a 400, the call is retried
    once **without** it rather than failing the user's request. Model families
    disagree about whether the floor is spelled ``none`` or ``minimal``, and a
    user losing their request over a parameter spelling is a worse outcome than
    one request costing provider-default effort. The retry logs loudly, because
    a service silently paying for default reasoning on every request is exactly
    the doubled bill this module exists to prevent.
    """
    api_key = app.config["OPENAI_API_KEY"]
    base_url = app.config["OPENAI_BASE_URL"]
    timeout = app.config["OPENAI_TIMEOUT_SECONDS"]
    url = f"{base_url}/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}"}

    def _post(effort: str | None):
        return requests.post(
            url,
            headers=headers,
            json=build_request_body(model_id, prompt, max_output_tokens, effort),
            timeout=timeout,
        )

    try:
        response = _post(reasoning_effort)
        if response.status_code == 400 and reasoning_effort is not None:
            app.logger.error(
                "Provider rejected reasoning_effort=%r for model %s; retrying without it. "
                "Requests will use the provider's DEFAULT reasoning effort, which is "
                "billed as output and may double the bill. Fix the value in "
                "app/prompts.py::REASONING_EFFORT.",
                reasoning_effort,
                model_id,
            )
            response = _post(None)
        response.raise_for_status()
    except requests.RequestException as exc:
        # Deliberately not interpolating the exception's own text: requests'
        # exceptions do not echo request headers today, but this is the one
        # place where an upstream change doing so would leak the key into a log.
        raise OpenAICallError(f"OpenAI request failed: {type(exc).__name__}") from exc

    return _parse(response.json())
