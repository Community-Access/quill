"""Optional AI harness packs (PRD §19, §18.5).

Each subpackage is a lazily-imported :class:`~quill.core.ai.harness.Harness` that
bridges a third-party agent SDK to QUILL's Safe Editor Tool Gateway and Permission
Broker. Packs are **optional extras**: an uninstalled pack reports
``is_available() == (False, "Install the X pack ...")`` and QUILL keeps working;
none is ever required, and none edits the buffer directly.

QUILL focuses on three SDKs — **OpenAI Agents**, **Claude Agent**, and **GitHub
Copilot** — which cover the field; other frameworks were intentionally dropped to
keep the surface small and well-tested.

Importing this package, and constructing a pack (``all_packs()``, ``register_all()``),
does NOT import any SDK. SDKs are only probed on demand via
:func:`quill.ai_packs._base.modules_missing` (called from ``is_available()``), which
does attempt a real import once a module's spec is located — needed to tell a genuinely
usable install from one merely present on disk (see that function's docstring) — before
the SDK is imported for real inside a session when the pack actually runs.
"""

from __future__ import annotations

from quill.ai_packs._base import SdkHarness
from quill.ai_packs.claude import ClaudeAgentHarness
from quill.ai_packs.copilot import CopilotHarness
from quill.ai_packs.openai_agents import OpenAIAgentsHarness

__all__ = [
    "SdkHarness",
    "CopilotHarness",
    "ClaudeAgentHarness",
    "OpenAIAgentsHarness",
    "all_packs",
    "register_all",
]


def all_packs() -> list[SdkHarness]:
    """Construct one instance of every pack (no SDK import happens here)."""
    return [
        CopilotHarness(),
        ClaudeAgentHarness(),
        OpenAIAgentsHarness(),
    ]


def register_all(registry: object) -> list[SdkHarness]:
    """Register every pack into ``registry``; return the packs.

    Registering an uninstalled pack is intentional: it appears in the Hub's
    Harnesses tab as available-to-install (``is_available()`` reports the reason),
    rather than vanishing silently.
    """
    packs = all_packs()
    for pack in packs:
        registry.register(pack)  # type: ignore[attr-defined]
    return packs
