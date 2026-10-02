"""The ChatGPT sign-in's saved state: one file per app, and who else is signed in.

Split out of :mod:`quill.core.ai.chatgpt_account` on 2026-10-02 (GATE-11),
when the state file became per-app: see :func:`_state_path`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from quill.core.storage import read_json, write_json_atomic

__all__ = ["ChatGptState", "load_state", "save_state", "sibling_sign_ins", "slug_for"]

_STATE_DIR = "ai"
_STATE_FILE = "chatgpt.json"


def slug_for(agent_name: str) -> str:
    """``"QUILL Lite"`` -> ``"quill-lite"``: the secrets-store name for an agent."""
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in agent_name.strip())
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned.strip("-") or "quill"


@dataclass(frozen=True, slots=True)
class ChatGptState:
    """Everything non-secret this app knows about its ChatGPT sign-in."""

    #: Stable per install and per app; OpenAI ties the dynamic registration to it.
    host_id: str = ""
    client_id: str = ""
    subject: str = ""
    email: str = ""
    scope: str = ""
    connected_at: str = ""
    #: The model requests use, chosen from the account's own list. Empty until
    #: the list has been read once; a request with no model says so.
    model: str = ""
    #: Whether OpenAI's hosted web search may be offered to the model. Off by
    #: default: a search is a second thing sent somewhere, and it is the
    #: person's to switch on.
    web_search: bool = False
    #: The app that signed in, for the sibling notice; filled on save.
    agent_name: str = ""

    @property
    def signed_in(self) -> bool:
        return bool(self.client_id and self.subject)

    @property
    def account_label(self) -> str:
        """The account as a person hears it: the email, or a neutral phrase."""
        return self.email or "your ChatGPT account"

    def to_dict(self) -> dict[str, Any]:
        return {
            "host_id": self.host_id,
            "client_id": self.client_id,
            "subject": self.subject,
            "email": self.email,
            "scope": self.scope,
            "connected_at": self.connected_at,
            "model": self.model,
            "web_search": self.web_search,
            "agent_name": self.agent_name,
        }

    @classmethod
    def from_dict(cls, data: object) -> ChatGptState:
        if not isinstance(data, dict):
            return cls()
        return cls(
            host_id=str(data.get("host_id", "") or ""),
            client_id=str(data.get("client_id", "") or ""),
            subject=str(data.get("subject", "") or ""),
            email=str(data.get("email", "") or ""),
            scope=str(data.get("scope", "") or ""),
            connected_at=str(data.get("connected_at", "") or ""),
            model=str(data.get("model", "") or ""),
            web_search=bool(data.get("web_search", False)),
            agent_name=str(data.get("agent_name", "") or ""),
        )


def _state_path(data_dir: Path, slug: str = "") -> Path:
    """The state file: one **per app** (``chatgpt-<slug>.json``) since 2026-10-02.

    Every QuillVille app shares one data folder, and the one ``chatgpt.json``
    they all wrote meant the second app to sign in overwrote the first app's
    client id and model while each kept its own refresh token -- so the first
    app believed it was signed in and could no longer refresh. The legacy file
    is still read when an app's own file does not exist yet.
    """
    if not slug:
        return data_dir / _STATE_DIR / _STATE_FILE
    return data_dir / _STATE_DIR / f"chatgpt-{slug}.json"


def load_state(data_dir: Path, slug: str = "") -> ChatGptState:
    try:
        own = _state_path(data_dir, slug)
        if slug and not own.exists():
            legacy = _state_path(data_dir)
            return ChatGptState.from_dict(read_json(legacy, default={}))
        return ChatGptState.from_dict(read_json(own, default={}))
    except OSError:
        return ChatGptState()


def save_state(data_dir: Path, state: ChatGptState, slug: str = "") -> None:
    path = _state_path(data_dir, slug)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json_atomic(path, state.to_dict())


def sibling_sign_ins(data_dir: Path, *, except_slug: str = "") -> list[str]:
    """The other QuillVille apps signed in with ChatGPT on this computer, by name.

    Each app signs in on its own (OpenAI shows the app's name on the consent
    page and in the person's ChatGPT settings), so a sibling's sign-in does not
    sign this app in -- but it does mean the browser is already signed in, and
    Continue with ChatGPT is one Allow rather than a password. The account
    window says so.
    """
    folder = data_dir / _STATE_DIR
    found: list[str] = []
    try:
        candidates = sorted(folder.glob("chatgpt-*.json"))
    except OSError:
        return found
    for path in candidates:
        slug = path.stem[len("chatgpt-") :]
        if not slug or slug == except_slug:
            continue
        try:
            state = ChatGptState.from_dict(read_json(path, default={}))
        except OSError:
            continue
        if state.signed_in:
            found.append(state.agent_name or slug.replace("-", " ").title())
    return found
