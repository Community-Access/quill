"""Which AI reads a Studio picture, and the consent that names it.

Two ways can read a screenshot or a sheet of video frames: the AI provider set
up in QUILL (``load_assistant_connection_settings``), and Studio's own ChatGPT
plan sign-in (:mod:`quill.core.studio_plan_vision`). With one, Studio uses it
without asking; with both, it asks which, starting on the last one chosen;
with neither, it offers to sign in with a ChatGPT plan through the family's
shared Use My ChatGPT Subscription window, rather than stopping at a refusal.
When the plan's usage is used up, Studio says so and offers ChatGPT's Usage
settings; it never moves to the provider by itself.

Safe Mode and AI Off refuse before any of this is looked at.
"""

from __future__ import annotations

import wx

from quill.core.paths import app_data_dir

_TITLE = "Choose the AI for this picture"


class StudioVisionRouteMixin:
    # -- what can read a picture ------------------------------------------------

    def _studio_chatgpt_account(self):
        account = getattr(self, "_studio_chatgpt", None)
        if account is None:
            from quill.core.ai.chatgpt_account import ChatGptAccount
            from quill.core.studio_plan_vision import STUDIO_AGENT

            account = ChatGptAccount(app_data_dir(), agent_name=STUDIO_AGENT)
            self._studio_chatgpt = account
        return account

    def _vision_candidates(self):
        """Every connection that can read a picture now: the plan first, then the provider."""
        from quill.core.assistant_ai import load_assistant_connection_settings
        from quill.core.studio_plan_vision import find_plan

        found = []
        plan = find_plan(self._studio_chatgpt_account())
        if plan is not None:
            found.append(plan)
        connection = load_assistant_connection_settings()
        if connection.provider.strip().lower() != "off":
            found.append(connection)
        return found

    def _automatic_vision_connection(self, preferences):
        """The connection automatic analysis was approved for, if it can still be used."""
        from quill.core.assistant_ai import load_assistant_connection_settings
        from quill.core.studio_capture_ai import connection_identity

        candidates = self._vision_candidates()
        approved = preferences.get("approved_connection")
        for candidate in candidates:
            if connection_identity(candidate) == approved:
                return candidate
        return candidates[0] if candidates else load_assistant_connection_settings()

    # -- choosing ---------------------------------------------------------------

    def _choose_vision_connection(self):
        """The connection to use, asking only when there is a real choice; or ``None``."""
        from quill.core.ai.model_manager import load_ai_enabled

        if self._safe_mode or not load_ai_enabled():
            self._announce("AI is disabled. Capture and local verification remain available.")
            return None
        candidates = self._vision_candidates()
        if not candidates:
            self._offer_plan_sign_in()
            return None
        if len(candidates) == 1:
            return candidates[0]
        return self._ask_which_connection(candidates)

    def _ask_which_connection(self, candidates):
        from quill.core.studio_capture_ai import (
            load_capture_ai_preferences,
            save_capture_ai_preferences,
        )
        from quill.core.studio_plan_vision import PLAN_PROVIDER

        labels = [_describe(candidate) for candidate in candidates]
        routes = [
            "plan" if candidate.provider == PLAN_PROVIDER else "provider"
            for candidate in candidates
        ]
        preferences = load_capture_ai_preferences()
        dialog = wx.SingleChoiceDialog(
            self.frame,
            "Two kinds of AI can read this picture. Which should Studio use?",
            _TITLE,
            labels,
        )
        last = preferences.get("vision_route")
        dialog.SetSelection(routes.index(last) if last in routes else 0)
        try:
            if self._show_modal_dialog(dialog, _TITLE) != wx.ID_OK:
                return None
            index = dialog.GetSelection()
        finally:
            dialog.Destroy()
        if index < 0:
            return None
        if preferences.get("vision_route") != routes[index]:
            preferences["vision_route"] = routes[index]
            save_capture_ai_preferences(preferences)
        return candidates[index]

    def _offer_plan_sign_in(self):
        from quill.core.studio_plan_vision import siblings_signed_in

        signed_in = siblings_signed_in(self._studio_chatgpt_account())
        already = ""
        if signed_in:
            verb = "is" if len(signed_in) == 1 else "are"
            already = (
                f"{' and '.join(signed_in)} {verb} already signed in on this computer, so "
                "this is usually one Allow in your browser.\n\n"
            )
        answer = self._show_message_box(
            "Studio has no AI to ask about this picture yet.\n\n"
            "If you pay for ChatGPT, Studio can use that plan: no key to paste and "
            "nothing to pay per request. Studio signs in on its own, as QUILL Studio. "
            "Sign in with your ChatGPT plan now?\n\n"
            + already
            + "Choose No to set up an AI provider in QUILL's AI menu instead.",
            "Sign in with your ChatGPT plan",
            wx.YES_NO | wx.ICON_QUESTION,
        )
        if answer in (wx.YES, wx.ID_YES):
            self.open_chatgpt_account()

    def _offer_plan_usage(self, url):
        """After the plan's limit: offer ChatGPT's Usage settings, and nothing else."""
        answer = self._show_message_box(
            "Your ChatGPT plan's usage limit has been reached. Open ChatGPT's Usage "
            "settings in your browser?",
            "ChatGPT plan usage",
            wx.YES_NO | wx.ICON_INFORMATION,
        )
        if answer in (wx.YES, wx.ID_YES):
            import webbrowser

            webbrowser.open(url)

    def _approve_capture_ai(self):
        """Choose the connection, then ask before the picture is sent."""
        from quill.core.studio_capture_ai import connection_identity
        from quill.core.studio_plan_vision import PLAN_PROVIDER

        connection = self._choose_vision_connection()
        if connection is None:
            return None
        identity = connection_identity(connection)
        if connection.provider == PLAN_PROVIDER:
            where = (
                f"Send this complete screenshot to {connection.label()}?\n"
                f"Model: {identity['model']}\nEndpoint: {identity['host']}\n\n"
            )
            cost = (
                "It goes straight to OpenAI on your account, under OpenAI's terms, and "
                "counts toward your ChatGPT plan's own usage; there is no separate charge.\n"
            )
        else:
            where = (
                f"Send this complete screenshot to {identity['provider']}?\n"
                f"Model: {identity['model']}\nEndpoint: {identity['host']}\n\n"
            )
            cost = (
                "The image and your conversation are sent to the endpoint above. Service "
                "charges may apply; Studio cannot reliably estimate this request's price.\n"
            )
        result = self._show_message_box(
            where + "The image may contain private information. No automatic redaction has been "
            "applied.\n"
            + cost
            + "AI observations are uncertain and do not verify privacy or correctness.",
            "Send screenshot to AI",
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION,
        )
        return connection if result in (wx.YES, wx.ID_YES) else None

    # -- Studio's own sign-in -----------------------------------------------------

    def open_chatgpt_account(self):
        """Use My ChatGPT Subscription, for Studio's own sign-in."""
        if self._safe_mode:
            self._announce("AI is disabled in Safe Mode.")
            return
        frame = getattr(self, "_chatgpt_frame", None)
        if frame:
            frame.Raise()
            return
        from quill.ui.hosted_ai_chatgpt import ChatGptFrame

        frame = ChatGptFrame(self.frame, self._studio_chatgpt_account(), self._announce)
        self._chatgpt_frame = frame
        frame.Show()


def _describe(connection):
    from quill.core.studio_capture_ai import connection_identity
    from quill.core.studio_plan_vision import PLAN_PROVIDER

    if connection.provider == PLAN_PROVIDER:
        return connection.label()[0].upper() + connection.label()[1:]
    identity = connection_identity(connection)
    return f"{identity['provider']} ({identity['model']}), the AI set up in QUILL"
