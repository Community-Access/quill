"""Mailer abstraction for magic-link auth (PRD 45.9).

Postmark is the default transactional email provider. The interface is tiny so
Postmark can be swapped for SES, Mailgun, or a self-hosted SMTP without touching
the auth flow. No email is ever sent without the user's action; there is no
marketing or engagement email (PRD 33.2, 45.9).

The email body is plain-text-first with a single, full link on its own line so
screen readers hear the link and purpose without parsing decorative HTML.
"""

from __future__ import annotations

import os
from typing import Protocol

DEFAULT_FROM = "QuillSync <signin@quillville.app>"


class Mailer(Protocol):
    def send_magic_link(self, email: str, link: str) -> None: ...


class LoggingMailer:
    """Dev/test mailer: prints the magic link instead of sending it.

    Use during development so the flow is fully exercisable without an email
    provider account. The link is the only thing that would be emailed.
    """

    def __init__(self, sink=None) -> None:
        self.sink = sink  # callable(email, link) for tests; None -> print

    def send_magic_link(self, email: str, link: str) -> None:
        if self.sink is not None:
            self.sink(email, link)
        else:
            print(f"[QuillSync] magic link for {email}: {link}")


class PostmarkMailer:
    """Postmark transactional email. Requires POSTMARK_API_KEY in the env.

    Uses the Postmark send API (https://postmarkapp.com). The API key is read
    from the environment and never logged. Fails closed: if no key is set, the
    link is not sent and the caller surfaces an error.
    """

    API_URL = "https://api.postmarkapp.com/email"

    def __init__(self, *, api_key: str | None = None, from_addr: str = DEFAULT_FROM,
                 requests_lib=None) -> None:
        self.api_key = api_key or os.environ.get("POSTMARK_API_KEY", "")
        self.from_addr = from_addr
        self.requests = requests_lib or _import_requests()

    def send_magic_link(self, email: str, link: str) -> None:
        if not self.api_key:
            raise RuntimeError("POSTMARK_API_KEY not set; cannot send magic link")
        if self.requests is None:
            raise RuntimeError(
                "requests library not installed; cannot send magic link via Postmark")
        body = (
            "Sign in to QuillSync\n\n"
            "Open this link to sign in on this device. It expires in 15 minutes "
            "and works once:\n\n"
            f"{link}\n\n"
            "If you did not request this, ignore this email. No password is needed.\n"
        )
        self.requests.post(
            self.API_URL,
            headers={"X-Postmark-Server-Token": self.api_key,
                     "Content-Type": "application/json"},
            json={"From": self.from_addr, "To": email,
                  "Subject": "QuillSync sign-in", "TextBody": body},
            timeout=10,
        )


def _import_requests():
    try:
        import requests  # type: ignore
        return requests
    except ImportError:
        return None