"""An :class:`~quill.core.ai.backend.AIBackend` over QUILL's hosted service.

This is the seam that lets **QUILL** reach the hosted tier, and it is why the
whole gateway client lives in the shared package rather than inside QuillLite.
CLAUDE.md's rule is that QuillLite may never be ahead of QUILL: a capability the
small product has and the big one cannot reach is backwards, and invisible.

Nothing registers this yet, and that is deliberate. QUILL already has a rich AI
story -- bring-your-own-key across five providers, local models, the agent
harness -- and adding a sixth provider to ``ALL_PROVIDERS`` or a sixth branch to
``make_default_backend()``'s cascade would change what an existing QUILL install
does on its next launch. That is a decision to take on purpose, with its own
review, rather than a side effect of shipping QuillLite's version. Until then
QUILL is not *behind*: it has more AI than QuillLite does, and this is the
one-line registration away whenever it is wanted.

The free tier is a narrower product than BYOK, and honestly so:

* **No streaming.** Answers arrive whole. ``AIBackend.respond_stream`` already
  degrades cleanly to one fragment, so nothing above has to know.
* **No conversation.** Each request is one passage and one instruction. There is
  no history to carry and no multi-turn context to pay for.
* **No tools.** The server will not accept them -- see
  ``app/openai_client.py``'s allowlist in the gateway repository.

A caller wanting any of those uses a BYOK provider, exactly as today.
"""

from __future__ import annotations

from quill.core.ai.backend import AIBackend
from quill.core.ai.gateway_client import GatewayClient
from quill.core.ai.gateway_errors import GatewayError

__all__ = ["GatewayBackend"]


class GatewayBackend(AIBackend):
    """Generate through QUILL's free hosted AI.

    ``feature`` decides which fixed, server-side instruction the passage is
    wrapped in. The client never sends an instruction of its own -- that is what
    stops a modified build using the service for something it was not opened
    for -- so the feature id is the whole of the caller's influence over the
    prompt.
    """

    name = "quill_gateway"

    def __init__(self, client: GatewayClient, *, feature: str = "summarize") -> None:
        self._client = client
        self._feature = feature

    def is_available(self) -> tuple[bool, str | None]:
        """Whether a request would be worth attempting.

        Answered from what this computer already knows -- is there a token --
        rather than by asking the server. A network round trip to decide whether
        to show a menu item would put a stall on opening a menu, and the real
        answer arrives with the first request anyway.
        """
        if not self._client.token:
            return False, (
                "This computer is not connected to QUILL's free AI. "
                "Choose Tools, AI, Sign In to connect it."
            )
        return True, None

    def respond(self, prompt: str) -> str:
        available, reason = self.is_available()
        if not available:
            raise RuntimeError(reason or "QUILL's free AI is not available.")
        try:
            text, _quota = self._client.ask(self._feature, prompt)
        except GatewayError as error:
            # Carries the coded message and its user_hint through unchanged:
            # every one of them is already a sentence written for a person.
            raise RuntimeError(str(error)) from error
        return text
