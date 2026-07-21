"""The optional AI Assistance layer for QUILL Social (PRD section 21).

AI here is optional, modular, inspectable, and reversible (PRD 21.1). Every
feature routes through :mod:`quill_social.services.ai.gateway`, which selects a
provider, refuses to run when AI is disabled, redacts secrets before anything
reaches a prompt, and emits a :class:`~quill_social.services.ai.gateway.Disclosure`
of exactly what would be sent. Writing tools return draft ``Proposal`` objects
that are never published without approval (PRD 21.4). Understanding features
always lead back to their source items (PRD 21.3, 12.6). All retrieved social
text is treated as untrusted data, never as instructions (PRD 21.7).

Nothing in this package makes a network call: a deterministic ``MockProvider``
stands in for a real model so the whole layer is testable, and live providers
are a documented boundary.
"""

from __future__ import annotations

from quill_social.services.ai.gateway import (
    AIGateway,
    AIProvider,
    Disclosure,
    GatewayResult,
    MockProvider,
    ProviderMode,
)

__all__ = [
    "AIGateway",
    "AIProvider",
    "Disclosure",
    "GatewayResult",
    "MockProvider",
    "ProviderMode",
]
