"""The single call site that ever talks to OpenAI.

Everything upstream of this module (auth, quota, size limits, model
selection) has already run by the time :func:`complete` is called --
this function's only job is the HTTP call itself and turning the
response into ``(text, tokens_in, tokens_out)``. Keeping this the *only*
place ``OPENAI_API_KEY`` is read means an audit of "does this key ever
leak" only has one call site to check.
"""

from __future__ import annotations

import requests


class OpenAICallError(Exception):
    """The upstream call failed. Never includes the API key in its message
    (the key is never part of any exception text this module raises)."""


def complete(app, model_id: str, prompt: str, max_output_tokens: int) -> tuple[str, int, int]:
    """Call OpenAI's chat completions endpoint with *prompt*, capped at
    *max_output_tokens*. Returns ``(text, tokens_in, tokens_out)`` using
    the provider's own reported token counts (never the client's, never
    our own estimate) for billing accuracy in :func:`app.limits.record_usage`.
    """
    api_key = app.config["OPENAI_API_KEY"]
    base_url = app.config["OPENAI_BASE_URL"]
    timeout = app.config["OPENAI_TIMEOUT_SECONDS"]

    try:
        response = requests.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": model_id,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_output_tokens,
            },
            timeout=timeout,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        # Never interpolate the raw exception's __str__ blindly if it could
        # ever echo request headers back -- requests' exceptions don't by
        # default, but keep this defensive rather than assume forever.
        raise OpenAICallError(f"OpenAI request failed: {type(exc).__name__}") from exc

    payload = response.json()
    try:
        text = payload["choices"][0]["message"]["content"]
        usage = payload["usage"]
        tokens_in = int(usage["prompt_tokens"])
        tokens_out = int(usage["completion_tokens"])
    except (KeyError, IndexError, TypeError) as exc:
        raise OpenAICallError("OpenAI returned an unexpected response shape") from exc

    return text, tokens_in, tokens_out
