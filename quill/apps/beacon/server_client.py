"""HTTP client for the hosted QuillSync server (PRD 45.2 tier 3).

Thin wrapper over ``requests`` that speaks the server's JSON contract. Used
by the QuillSync client as the hosted transport; the BYO folder transport
(``quill.apps.beacon.sync.FolderTransport``) is the no-account tier.

Network calls are isolated here so the engine stays pure and testable.
"""

from __future__ import annotations

from typing import Any

import requests


class ServerClient:
    def __init__(
        self, base_url: str, device_token: str, *, session: requests.Session | None = None
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.device_token = device_token
        self.session = session or requests.Session()

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.device_token}", "Content-Type": "application/json"}

    @staticmethod
    def request_magic_link(base_url: str, email: str, *, session=None) -> dict:
        s = session or requests
        r = s.post(f"{base_url.rstrip('/')}/auth/request", json={"email": email}, timeout=10)
        r.raise_for_status()
        return r.json()

    @staticmethod
    def verify_magic_link(
        base_url: str, token: str, device: str = "device", *, session=None
    ) -> dict:
        s = session or requests
        r = s.get(
            f"{base_url.rstrip('/')}/auth/verify",
            params={"token": token, "device": device},
            timeout=10,
        )
        r.raise_for_status()
        return r.json()

    def push(self, commits: list[dict], objects: dict[str, bytes]) -> dict:
        import base64

        body = {
            "commits": commits,
            "objects": {h: base64.b64encode(b).decode("ascii") for h, b in objects.items()},
        }
        r = self.session.post(
            f"{self.base_url}/sync/push", json=body, headers=self._headers(), timeout=30
        )
        r.raise_for_status()
        return r.json()

    def pull(self, have: list[str]) -> dict[str, Any]:
        import base64

        r = self.session.post(
            f"{self.base_url}/sync/pull", json={"have": have}, headers=self._headers(), timeout=30
        )
        r.raise_for_status()
        data = r.json()
        # decode objects back to bytes
        data["objects"] = {h: base64.b64decode(b) for h, b in (data.get("objects") or {}).items()}
        return data

    def hints(self) -> dict:
        r = self.session.get(f"{self.base_url}/sync/hints", headers=self._headers(), timeout=10)
        r.raise_for_status()
        return r.json()
