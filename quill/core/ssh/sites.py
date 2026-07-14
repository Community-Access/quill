"""Site manager for edit-over-SSH (issue #139).

Stores reusable connection profiles: a friendly name, host/port, username, how
to authenticate, an optional private-key path, and a default remote directory to
open into.

Security: passwords are deliberately *not* persisted here. Saving a plaintext
password to a JSON file in the app-data area would expose it to anything that can
read the user's profile. Instead a saved site records how to authenticate (key
file, SSH agent, or "prompt for a password"), and any password is entered at
connect time and held only in memory.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from quill.core.paths import app_data_dir
from quill.core.storage import read_json, write_json_atomic

AUTH_PASSWORD = "password"
AUTH_KEY = "key"
AUTH_AGENT = "agent"
_VALID_AUTH = {AUTH_PASSWORD, AUTH_KEY, AUTH_AGENT}

_SITES_FILENAME = "ssh_sites.json"
DEFAULT_PORT = 22


@dataclass(slots=True)
class SiteConfig:
    """A saved SSH connection profile. Never holds a plaintext password."""

    name: str
    host: str
    port: int = DEFAULT_PORT
    username: str = ""
    auth: str = AUTH_PASSWORD
    key_path: str = ""
    default_dir: str = ""

    def normalised(self) -> SiteConfig:
        """Return a copy with a sane port and a recognised auth method."""
        port = self.port if isinstance(self.port, int) and self.port > 0 else DEFAULT_PORT
        auth = self.auth if self.auth in _VALID_AUTH else AUTH_PASSWORD
        return SiteConfig(
            name=self.name.strip(),
            host=self.host.strip(),
            port=port,
            username=self.username.strip(),
            auth=auth,
            key_path=self.key_path.strip(),
            default_dir=self.default_dir.strip(),
        )


def _sites_path() -> Path:
    return app_data_dir() / _SITES_FILENAME


def _from_dict(data: dict) -> SiteConfig:
    return SiteConfig(
        name=str(data.get("name", "")),
        host=str(data.get("host", "")),
        port=int(data.get("port", DEFAULT_PORT) or DEFAULT_PORT),
        username=str(data.get("username", "")),
        auth=str(data.get("auth", AUTH_PASSWORD)),
        key_path=str(data.get("key_path", "")),
        default_dir=str(data.get("default_dir", "")),
    ).normalised()


def load_sites() -> list[SiteConfig]:
    """Return saved sites sorted by friendly name (case-insensitive)."""
    raw = read_json(_sites_path(), [])
    # Accept the versioned envelope and the legacy bare list (back-compat).
    items = raw.get("sites", []) if isinstance(raw, dict) else raw
    if not isinstance(items, list):
        return []
    sites = [_from_dict(item) for item in items if isinstance(item, dict) and item.get("name")]
    return sorted(sites, key=lambda site: site.name.lower())


def save_sites(sites: list[SiteConfig]) -> None:
    base = app_data_dir()
    payload = {"schema_version": 1, "sites": [asdict(site.normalised()) for site in sites]}
    write_json_atomic(_sites_path(), payload, base=base)


def upsert_site(site: SiteConfig) -> list[SiteConfig]:
    """Add ``site`` or replace an existing one with the same name. Returns the new list."""
    site = site.normalised()
    others = [existing for existing in load_sites() if existing.name.lower() != site.name.lower()]
    others.append(site)
    save_sites(others)
    return load_sites()


def delete_site(name: str) -> list[SiteConfig]:
    remaining = [site for site in load_sites() if site.name.lower() != name.strip().lower()]
    save_sites(remaining)
    return remaining
