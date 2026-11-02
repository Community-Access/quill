"""Ask before a hosted-AI request goes somewhere new (2026-10-16).

Mixed into :class:`quill.ui.hosted_ai_service.AiService`, so QUILL and QUILL
Lite share it, as they share everything else in the hosted AI.

The service decides the route on every request, from live state: a ChatGPT
sign-in wins, then the listener's own key for the provider they chose, then
QUILL's free AI (:attr:`AiService.route`). Live state is what keeps that honest
-- and it is also how a request could quietly change company. A ChatGPT sign-in
that stops working, or an own key that disappears from the credential store,
and the very next Rewrite goes to QUILL's free service instead; a key saved in
another window, and the next one goes to OpenAI. Each is a different company
receiving the person's text, and nothing said so.

So the route a request takes is remembered for the session, and a request that
would take a different one -- without the listener having changed it here --
is a substitution (:func:`quill.core.ai.fallback.plan_substitution`). Every
hosted substitution sends text to a different company, so every one asks first:
a Yes/No box whose text is the plan's announcement, No the default. Yes, and the
new route is simply the route from then on, so the question is asked once. No,
and nothing is sent; the request's own error path says so.

Changing the route deliberately -- signing in or out of ChatGPT, saving or
removing a key in Use My Own AI Key -- calls :meth:`route_chosen`, so a choice
made a moment ago is never questioned as if it were a fallback.

What this cannot see: a change between sessions. The first request after
starting has nothing to compare against, and goes where the route says, as it
always has.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

__all__ = ["RouteGuardMixin"]


class RouteGuardMixin:
    """Remembers the route in use and asks before a request leaves it."""

    route: str
    own_key_provider: str

    #: Replaced in tests, and by any host that has its own way of asking.
    confirm_route_change: Callable[[str], bool] | None = None

    def route_names(self, route: str = "") -> tuple[str, str]:
        """``(what the route is called, which company receives the text)``."""
        route = route or self.route
        if route == "chatgpt":
            return "your ChatGPT subscription", "OpenAI"
        if route == "copilot":
            return "your GitHub Copilot", "GitHub"
        if route == "own_key":
            from quill.core.ai.own_key import provider_name

            company = provider_name(self.own_key_provider)
            return f"your own {company} key", company
        return "QUILL's free AI", "QUILL's free AI service"

    def route_chosen(self) -> None:
        """The listener just chose the route (signed in or out, saved or removed
        a key): whatever it now is, it is theirs, not a fallback."""
        self._route_in_use = (self.route, self.route_names()[0])

    def route_allowed(self, on_error: Callable[[str], None]) -> bool:
        """Whether a request may go out on the current route. Asks first when
        the route has changed under the listener; on No, tells *on_error*."""
        from quill.core.ai.fallback import plan_substitution

        current = (self.route, self.route_names()[0])
        previous: Any = getattr(self, "_route_in_use", None)
        if previous is None or previous == current:
            self._route_in_use = current
            return True
        chosen = str(previous[1])
        plan = plan_substitution(
            chosen=chosen[:1].upper() + chosen[1:],
            substitute=current[1],
            substitute_is_local=False,
            destination=self.route_names()[1],
        )
        if plan.requires_consent and not self._confirm_route(plan.announcement):
            on_error(
                f"Nothing was sent. Your requests were going to {chosen}, which is "
                "not available now. Set it up again from the AI menu, or ask again "
                "and choose Yes to use the other one."
            )
            return False
        self._route_in_use = current
        return True

    def _confirm_route(self, question: str) -> bool:
        confirm = self.confirm_route_change
        if confirm is not None:
            return bool(confirm(question))
        import wx

        from quill.ui.dialog_contract import show_message_box

        answer = show_message_box(
            question,
            "Send to a Different AI?",
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION,
            wx.GetActiveWindow(),
        )
        return answer == wx.YES
