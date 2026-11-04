"""The WordPress sites a person has connected (wordpress.md 4.4).

Many sites are a requirement, not an extra, so the list is the model and the
"default site" is only where New and Open start. A document carries its site's
id for life; switching the default never moves it.

Secrets -- an application password or a WordPress.com token -- are kept in
Windows Credential Manager by the existing publishing secret store, keyed by
the site's id. This file holds names and addresses only.

On first load, connections saved by the older publishing framework are
imported once, so nobody connects twice.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse
from uuid import uuid4

from quill.core.paths import app_data_dir
from quill.core.storage import read_json, write_json_atomic
from quill.core.wordpress.api import Opener, SiteAddress, SiteAuth, WordPressApi

SiteKind = Literal["self_hosted", "wpcom"]

SITES_FILE = "wordpress-sites.json"


@dataclass(frozen=True)
class SiteProfile:
    id: str
    name: str
    site_url: str
    username: str = ""
    kind: SiteKind = "self_hosted"
    wpcom_site: str = ""
    role: str = ""
    wp_version: str = ""
    announce_waiting_comments: bool = True
    ask_add_to_menu: bool = True
    #: Say "4 new responses to Event registration" on first use (wordpress.md 17a.8).
    announce_new_responses: bool = True

    @property
    def address(self) -> SiteAddress:
        return SiteAddress(self.site_url, self.wpcom_site if self.kind == "wpcom" else "")

    @property
    def host(self) -> str:
        return (urlparse(self.site_url).hostname or self.site_url).lower()

    def spoken(self) -> str:
        role = f", {self.role}" if self.role else ""
        where = "WordPress.com" if self.kind == "wpcom" else self.host
        return f"{self.name}{role}, {where}"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SiteProfile:
        kind = str(data.get("kind", "self_hosted"))
        return cls(
            id=str(data.get("id", "")) or new_site_id(),
            name=str(data.get("name", "")) or _host_of(str(data.get("site_url", ""))),
            site_url=str(data.get("site_url", "")).rstrip("/"),
            username=str(data.get("username", "")),
            kind="wpcom" if kind == "wpcom" else "self_hosted",
            wpcom_site=str(data.get("wpcom_site", "")),
            role=str(data.get("role", "")),
            wp_version=str(data.get("wp_version", "")),
            announce_waiting_comments=bool(data.get("announce_waiting_comments", True)),
            ask_add_to_menu=bool(data.get("ask_add_to_menu", True)),
            announce_new_responses=bool(data.get("announce_new_responses", True)),
        )


@dataclass
class SiteStore:
    sites: list[SiteProfile] = field(default_factory=list)
    default_id: str = ""

    def get(self, site_id: str) -> SiteProfile | None:
        return next((s for s in self.sites if s.id == site_id), None)

    @property
    def default(self) -> SiteProfile | None:
        return self.get(self.default_id) or (self.sites[0] if self.sites else None)

    def upsert(self, profile: SiteProfile) -> None:
        for index, existing in enumerate(self.sites):
            if existing.id == profile.id:
                self.sites[index] = profile
                break
        else:
            self.sites.append(profile)
        if not self.default_id:
            self.default_id = profile.id

    def remove(self, site_id: str) -> None:
        self.sites = [s for s in self.sites if s.id != site_id]
        if self.default_id == site_id:
            self.default_id = self.sites[0].id if self.sites else ""

    def rename(self, site_id: str, name: str) -> None:
        profile = self.get(site_id)
        if profile is not None and name.strip():
            self.upsert(replace(profile, name=name.strip()))

    def match_url(self, url: str) -> SiteProfile | None:
        """The saved site a web address belongs to (Open by Web Address, 5.2).

        Matches by host, ignoring ``www.``, and prefers the longest path prefix
        so a site at ``example.org/blog`` wins over one at ``example.org``.
        """
        parsed = urlparse(url.strip())
        host = _bare_host(parsed.hostname or "")
        if not host:
            return None
        best: SiteProfile | None = None
        best_len = -1
        for site in self.sites:
            site_parsed = urlparse(site.site_url)
            hosts = {_bare_host(site_parsed.hostname or "")}
            if site.wpcom_site:
                hosts.add(_bare_host(site.wpcom_site))
            if host not in hosts:
                continue
            base_path = site_parsed.path.rstrip("/")
            if parsed.path.startswith(base_path) and len(base_path) > best_len:
                best, best_len = site, len(base_path)
        return best


def new_site_id() -> str:
    return "wp-" + uuid4().hex[:12]


def sites_path(base: Path | None = None) -> Path:
    return (base or app_data_dir()) / SITES_FILE


def load_sites(base: Path | None = None) -> SiteStore:
    path = sites_path(base)
    raw = read_json(path, default=None)
    if not isinstance(raw, dict):
        store = _import_publishing_connections()
        if store.sites:
            save_sites(store, base)
        return store
    sites = [SiteProfile.from_dict(s) for s in raw.get("sites", []) if isinstance(s, dict)]
    return SiteStore(sites, str(raw.get("default_id", "")))


def save_sites(store: SiteStore, base: Path | None = None) -> None:
    write_json_atomic(
        sites_path(base),
        {"sites": [asdict(s) for s in store.sites], "default_id": store.default_id},
    )


def api_for(
    profile: SiteProfile,
    *,
    secret_loader: Callable[[str], str] | None = None,
    opener: Opener | None = None,
) -> WordPressApi:
    """A signed client for *profile*, with its secret from Credential Manager."""
    load = secret_loader or _load_secret
    secret = load(profile.id)
    auth = (
        SiteAuth("bearer", secret=secret)
        if profile.kind == "wpcom" and not profile.username
        else SiteAuth("app_password", profile.username, secret)
    )
    return WordPressApi(profile.address, auth, opener=opener, site_name=profile.name)


def save_secret(site_id: str, secret: str) -> None:
    from quill.core.publishing import save_publishing_secret

    save_publishing_secret(site_id, secret)


def forget_secret(site_id: str) -> None:
    from quill.core.publishing import clear_publishing_secret

    clear_publishing_secret(site_id)


def _load_secret(site_id: str) -> str:
    from quill.core.publishing import load_publishing_secret

    return load_publishing_secret(site_id)


def _import_publishing_connections() -> SiteStore:
    try:
        from quill.core.publishing import load_publishing_connections
    except ImportError:  # pragma: no cover - the framework ships with QUILL
        return SiteStore()
    try:
        old = load_publishing_connections()
    except Exception:  # noqa: BLE001 - a broken old file must not block WordPress
        return SiteStore()
    store = SiteStore()
    for conn in old.connections:
        if conn.provider_id != "wordpress" or not conn.site_url:
            continue
        # Same id, so the secret already saved under it keeps working.
        store.upsert(
            SiteProfile(
                id=conn.id,
                name=conn.label
                if conn.label and conn.label != "WordPress"
                else _host_of(conn.site_url),
                site_url=conn.site_url.rstrip("/"),
                username=conn.account_identifier,
            )
        )
    if old.current_connection_id and store.get(old.current_connection_id):
        store.default_id = old.current_connection_id
    return store


def _host_of(url: str) -> str:
    return urlparse(url).hostname or url


def _bare_host(host: str) -> str:
    host = host.lower().strip()
    return host[4:] if host.startswith("www.") else host
