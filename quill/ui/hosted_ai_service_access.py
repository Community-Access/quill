"""Lazy access to the shared hosted-AI service."""

from __future__ import annotations

from typing import Any

__all__ = ["HostedAiServiceMixin"]


class HostedAiServiceMixin:
    """Create the app's one service and attach the active window announcer."""

    def _ai_host(self) -> Any: ...

    def _ai_service(self) -> Any:
        service = getattr(self._ai_host(), "ai_service", None)
        if service is None:
            from quill.ui.hosted_ai_service import AiService

            service = AiService(self._ai_host())
            self._ai_host().ai_service = service
        announce = getattr(self, "_announce", None)
        if callable(announce):
            service.route_announce = announce
        return service
