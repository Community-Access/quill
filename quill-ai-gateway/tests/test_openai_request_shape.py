"""The no-tools gate: what may appear in a request to the provider.

This is the cheapest test in the suite and the most expensive one to be
missing. OpenAI's hosted web search bills at $10 per thousand calls. On this
service's modelled traffic -- 50,000 requests a month -- turning it on for every
request would cost about $500 a month against roughly $30 of actual model usage:
**sixteen times the entire rest of the bill**, arriving as a line item nobody
was watching for.

The defence is not "do not enable it by default". It is that the request body
has a fixed shape, and adding anything to it fails the build. A key that
expensive should not be addable without a test turning red and a person
deciding it is worth it.
"""

from __future__ import annotations

import pytest
from app.openai_client import ALLOWED_BODY_KEYS, build_request_body
from app.prompts import (
    ALLOWED_EFFORTS,
    FEATURES,
    REASONING_EFFORT,
    SHIPPED_FEATURES,
    reasoning_effort_for,
)

#: Things that cost money, leak content, or change the shape of the product,
#: which must never appear in an outgoing body. Named explicitly rather than
#: relying only on the allowlist, so a future reader sees *what* is being kept
#: out and not merely that something is.
FORBIDDEN_KEYS = (
    "tools",
    "tool_choice",
    "functions",
    "function_call",
    "web_search_options",
    "file_search",
    "attachments",
    "store",
    "metadata",
    "parallel_tool_calls",
    "response_format",
    "stream",
)


def test_the_body_contains_only_allowlisted_keys():
    body = build_request_body("gpt-6-luna", "hello", 500, "none")
    assert set(body) <= ALLOWED_BODY_KEYS, (
        f"Unapproved keys in the outgoing request: {sorted(set(body) - ALLOWED_BODY_KEYS)}. "
        "Adding one is a cost decision, not a code detail -- see this module's docstring."
    )


@pytest.mark.parametrize("key", FORBIDDEN_KEYS)
def test_expensive_and_leaky_keys_are_never_sent(key):
    body = build_request_body("gpt-6-luna", "hello", 500, "none")
    assert key not in body


def test_the_allowlist_itself_has_not_grown():
    """Pinned. If this fails, somebody widened the allowlist -- which may be
    correct, but must be a deliberate change with a cost justification, not a
    side effect of another edit."""
    assert ALLOWED_BODY_KEYS == {
        "model",
        "messages",
        "max_completion_tokens",
        "reasoning_effort",
    }


def test_output_is_capped_with_max_completion_tokens_not_max_tokens():
    """Reasoning models reject the older ``max_tokens`` parameter outright, so
    this is a correctness bug as well as a cost one: every request would fail."""
    body = build_request_body("gpt-6-luna", "hello", 500, "none")
    assert body["max_completion_tokens"] == 500
    assert "max_tokens" not in body


def test_omitting_the_effort_omits_the_key_entirely():
    """The retry path when a provider rejects the parameter's spelling."""
    body = build_request_body("gpt-6-luna", "hello", 500, None)
    assert "reasoning_effort" not in body


def test_the_client_prompt_is_the_whole_message_and_nothing_else():
    """There is exactly one message and it is the one we built. A second
    message -- a system role, a prior turn -- would be a way for a caller to
    supply instructions, which is the thing app/prompts.py exists to prevent."""
    body = build_request_body("gpt-6-luna", "the prompt text", 500, "none")
    assert body["messages"] == [{"role": "user", "content": "the prompt text"}]


@pytest.mark.parametrize("feature", sorted(FEATURES))
def test_every_feature_has_a_floored_reasoning_effort(feature):
    """Reasoning is billed as output and never appears in the answer, so a
    feature that inherits the provider's default (medium) roughly doubles the
    bill invisibly. Every feature names its own, and none may exceed ``low``."""
    assert REASONING_EFFORT[feature] in ALLOWED_EFFORTS


def test_an_unknown_feature_falls_back_to_no_reasoning():
    """The fallback must be the floor, not the provider's default -- a typo in
    a feature id should cost nothing extra, not twice as much."""
    assert reasoning_effort_for("not-a-real-feature") == "none"


def test_the_four_transformation_features_do_no_reasoning_at_all():
    """Summarize, rewrite, proofread and explain all transform text the user
    supplied. There is nothing to reason about, and paying for thinking on them
    is pure loss."""
    for feature in ("summarize", "rewrite", "proofread", "explain"):
        assert REASONING_EFFORT[feature] == "none"


def test_the_five_shipped_features_all_have_templates():
    from app.prompts import TEMPLATES

    for feature in SHIPPED_FEATURES:
        assert feature in TEMPLATES
        assert TEMPLATES[feature].strip()
