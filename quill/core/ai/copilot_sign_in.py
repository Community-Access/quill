"""Signing this app in to My GitHub Copilot: the device code, the wait, the token.

The wx-free half of the Copilot row's sign-in step in Choose Your AI
(codex.md 10A.3, 10A.12). The window shows the code, puts it on the
clipboard and opens GitHub's page; this module asks GitHub for the code, waits
for the person to approve it, and keeps the token in this app's own store
entry (:func:`quill.core.ai.copilot_auth.persist_token`) -- never in the
environment and never in the repository features' entry.

**Per app.** Every QuillVille app has its own OAuth App registration and its
own token (decisions 10, 11, 16). An app with no client id cannot sign in at
all: :meth:`CopilotSignIn.request_code` raises
:class:`~quill.core.ai.copilot_auth.CopilotSignInUnavailable` before any
network call, and the window says so in one sentence.

**Cancel stops the wait.** :meth:`CopilotSignIn.wait` sleeps on a
``threading.Event``; setting it ends the polling at once, so Cancel never
leaves a thread polling GitHub for fifteen minutes.

**After a sign-in** both marks GitHub left on this app ("signed out by GitHub",
"not available for your account") are cleared
(:func:`quill.core.ai.copilot_state.clear_marks`), because a fresh sign-in is
the person's answer to both.

Both calls block: run them on a worker thread. wx-free and strict-typed.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from quill.core.ai import copilot_auth, copilot_state
from quill.core.ai.device_login import (
    STATUS_AUTHORIZED,
    STATUS_DENIED,
    STATUS_EXPIRED,
    DeviceCodeGrant,
    request_device_code,
    run_device_login,
)
from quill.core.error_codes import CodedError

__all__ = ["CopilotSignIn", "CopilotSignInFailed", "SignInCancelled", "spoken_code"]

Poster = Callable[[str, dict[str, str]], dict[str, Any]]


class CopilotSignInFailed(CodedError):
    """The device flow ended without a token; ``args[0]`` is the sentence to say."""

    code = "QUILL-AI-COPILOT-SIGNIN-FAILED"
    user_hint = "Choose Open the Page again for a new code, or Cancel."


class SignInCancelled(CodedError):
    """The person pressed Cancel while GitHub was being asked."""

    code = "QUILL-AI-COPILOT-SIGNIN-CANCELLED"


def spoken_code(user_code: str) -> str:
    """The code as separate characters, so a reader says each one.

    The same spacing as :attr:`quill.ui.hosted_ai_service.SignInCode.spoken`:
    ``ABCD-1234`` read as a word is a word nobody can type back.
    """
    return " ".join(user_code.replace("-", " dash "))


def _default_poster() -> Poster:
    from quill.core.ai.oauth_poster import post_form

    return post_form


class CopilotSignIn:
    """One sign-in attempt for one app. Make a new one for each attempt."""

    def __init__(
        self,
        agent_name: str = copilot_auth.DEFAULT_AGENT_NAME,
        *,
        data_dir: Path | None = None,
        poster: Poster | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.agent_name = agent_name or copilot_auth.DEFAULT_AGENT_NAME
        self.data_dir = data_dir
        self._poster = poster or _default_poster()
        self._clock = clock
        self.cancelled = threading.Event()

    def available(self) -> bool:
        """Whether this app has a GitHub registration to sign in with."""
        return copilot_auth.is_configured(self.agent_name)

    def request_code(self) -> DeviceCodeGrant:
        """Ask GitHub for a code. Raises ``CopilotSignInUnavailable`` with no client id."""
        config = copilot_auth.github_device_flow_config(self.agent_name)
        try:
            return request_device_code(config, poster=self._poster)
        except CodedError:
            raise
        except Exception as error:  # noqa: BLE001 - the network, worded once
            raise CopilotSignInFailed(
                "GitHub did not give a sign-in code. Check the connection and try again."
            ) from error

    def cancel(self) -> None:
        """Stop waiting; :meth:`wait` raises :class:`SignInCancelled` at once."""
        self.cancelled.set()

    def _sleep(self, seconds: float) -> None:
        if self.cancelled.wait(seconds):
            raise SignInCancelled("Sign-in cancelled.")

    def wait(self, grant: DeviceCodeGrant) -> None:
        """Wait for the person to approve *grant*, then keep this app's token.

        Returns when signed in. Raises :class:`SignInCancelled` on Cancel and
        :class:`CopilotSignInFailed` with a sentence for anything else.
        """
        config = copilot_auth.github_device_flow_config(self.agent_name)
        if self.cancelled.is_set():
            raise SignInCancelled("Sign-in cancelled.")
        try:
            result = run_device_login(
                config, grant, poster=self._poster, clock=self._clock, sleeper=self._sleep
            )
        except CodedError:
            raise
        except Exception as error:  # noqa: BLE001 - the network, worded once
            raise CopilotSignInFailed(
                "GitHub stopped answering before the sign-in finished. Nothing was saved."
            ) from error
        if result.status == STATUS_EXPIRED:
            raise CopilotSignInFailed("That code expired before it was used. Nothing was saved.")
        if result.status == STATUS_DENIED:
            raise CopilotSignInFailed(
                "The sign-in was refused on GitHub's page. Nothing was saved."
            )
        tokens = result.tokens or {}
        token = str(tokens.get("access_token", "") or "")
        if result.status != STATUS_AUTHORIZED or not token:
            detail = (result.error or "").strip().rstrip(".")
            said = f"GitHub did not finish the sign-in: {detail}." if detail else ""
            raise CopilotSignInFailed(said or "GitHub did not finish the sign-in.")
        if not copilot_auth.persist_token(token, self.agent_name):
            raise CopilotSignInFailed(
                "GitHub approved the sign-in, but it could not be stored securely on "
                "this computer, so nothing was saved."
            )
        copilot_state.clear_marks(self.agent_name, data_dir=self.data_dir)
