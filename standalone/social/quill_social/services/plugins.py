"""Plugin system: manifests, permissions, safe mode, and crash isolation (PRD 34).

The registry loads and validates plugin manifests, enforces the permissions a
plugin declares, and keeps the app resilient to bad plugins:

- Declared permissions are the only permissions a plugin has. Credentials are
  never granted by default -- a plugin must declare the ``credentials``
  permission explicitly, and the host still decides whether to honor it
  (PRD 34, "avoid direct credential access by default").
- Safe mode disables every third-party plugin at once, leaving only first-party
  (bundled) plugins active, so a user can always boot into a trusted state.
- ``safe_call`` isolates a failing plugin: an exception marks the plugin
  ``degraded`` (and disables it) instead of crashing the host (PRD 34, "isolate
  crashes").

Enabled/disabled/degraded state is persisted through the document store under
kind ``"plugin"`` so choices survive restarts. This module is wx-free and does
no network I/O.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

# The plugin kinds QUILL can host (PRD 34).
PLUGIN_KINDS = (
    "network_adapter",
    "importer",
    "exporter",
    "ai_provider",
    "media_resolver",
    "soundpack",
    "composer_tool",
    "folder_rule",
    "automation",
    "connector",
    "a11y",
)

# Fields a manifest must supply; declared_permissions may be empty.
_REQUIRED_FIELDS = ("id", "name", "version", "kind", "entry")

# The permission a plugin must explicitly declare to touch stored credentials;
# never granted implicitly (PRD 34).
CREDENTIAL_PERMISSION = "credentials"

_DOC_KIND = "plugin"


class PluginError(Exception):
    """A manifest validation or plugin-lifecycle failure."""


@dataclass
class PluginManifest:
    """A plugin's declared identity, kind, and permissions (PRD 34)."""

    id: str = ""
    name: str = ""
    version: str = ""
    kind: str = "composer_tool"
    declared_permissions: list[str] = field(default_factory=list)
    entry: str = ""
    first_party: bool = False  # bundled/trusted; survives safe mode

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "kind": self.kind,
            "declared_permissions": list(self.declared_permissions),
            "entry": self.entry,
            "first_party": self.first_party,
        }

    @classmethod
    def from_dict(cls, d: dict) -> PluginManifest:
        return cls(
            id=d.get("id", ""),
            name=d.get("name", ""),
            version=d.get("version", ""),
            kind=d.get("kind", "composer_tool"),
            declared_permissions=list(d.get("declared_permissions", [])),
            entry=d.get("entry", ""),
            first_party=bool(d.get("first_party", False)),
        )

    @classmethod
    def validate(cls, d: dict) -> PluginManifest:
        """Parse and validate a manifest dict, raising :class:`PluginError`."""
        for name in _REQUIRED_FIELDS:
            if not d.get(name):
                raise PluginError(f"manifest missing required field: {name}")
        kind = d.get("kind")
        if kind not in PLUGIN_KINDS:
            raise PluginError(f"unknown plugin kind: {kind!r}")
        perms = d.get("declared_permissions", [])
        if not isinstance(perms, list):
            raise PluginError("declared_permissions must be a list")
        return cls.from_dict(d)


@dataclass
class PluginState:
    """Persisted, per-plugin enable/degrade state."""

    enabled: bool = True
    degraded: bool = False
    last_error: str = ""


class PluginRegistry:
    """Loads plugins, enforces permissions, and isolates failures (PRD 34).

    Constructed with the document store and an optional ``safe_mode`` flag. When
    safe mode is on, every third-party plugin reports disabled regardless of its
    persisted state; first-party plugins stay available.
    """

    def __init__(self, store, *, safe_mode: bool = False) -> None:
        self.store = store
        self.safe_mode = safe_mode
        self._plugins: dict[str, PluginManifest] = {}

    # -- loading --------------------------------------------------------------

    def load(self, manifest: dict | PluginManifest) -> PluginManifest:
        """Validate (if needed) and register a manifest; persists default state."""
        m = manifest if isinstance(manifest, PluginManifest) else PluginManifest.validate(
            manifest
        )
        if not m.id:
            raise PluginError("manifest missing required field: id")
        self._plugins[m.id] = m
        if self.store.get_document(_DOC_KIND, m.id) is None:
            self._save_state(m.id, PluginState(enabled=True))
        return m

    def get(self, plugin_id: str) -> PluginManifest | None:
        return self._plugins.get(plugin_id)

    def _resolve_id(self, plugin: str | PluginManifest) -> str:
        return plugin.id if isinstance(plugin, PluginManifest) else plugin

    # -- state persistence ----------------------------------------------------

    def _save_state(self, plugin_id: str, state: PluginState) -> None:
        self.store.put_document(
            _DOC_KIND,
            plugin_id,
            {
                "enabled": state.enabled,
                "degraded": state.degraded,
                "last_error": state.last_error,
            },
        )

    def state(self, plugin: str | PluginManifest) -> PluginState:
        doc = self.store.get_document(_DOC_KIND, self._resolve_id(plugin)) or {}
        return PluginState(
            enabled=bool(doc.get("enabled", True)),
            degraded=bool(doc.get("degraded", False)),
            last_error=doc.get("last_error", ""),
        )

    def enable(self, plugin: str | PluginManifest) -> None:
        """Enable a plugin and clear any degraded marker."""
        self._save_state(self._resolve_id(plugin), PluginState(enabled=True))

    def disable(self, plugin: str | PluginManifest) -> None:
        st = self.state(plugin)
        st.enabled = False
        self._save_state(self._resolve_id(plugin), st)

    # -- effective status -----------------------------------------------------

    def is_enabled(self, plugin: str | PluginManifest) -> bool:
        """Whether a plugin is active right now, honoring safe mode + degrade."""
        pid = self._resolve_id(plugin)
        manifest = self._plugins.get(pid)
        if manifest is None:
            return False
        if self.safe_mode and not manifest.first_party:
            return False
        st = self.state(pid)
        return st.enabled and not st.degraded

    def is_degraded(self, plugin: str | PluginManifest) -> bool:
        return self.state(plugin).degraded

    def enabled_plugins(self) -> list[PluginManifest]:
        return [m for m in self._plugins.values() if self.is_enabled(m)]

    # -- permissions ----------------------------------------------------------

    def check_permission(self, plugin: str | PluginManifest, permission: str) -> bool:
        """True only if the plugin declared ``permission`` (PRD 34)."""
        manifest = plugin if isinstance(plugin, PluginManifest) else self._plugins.get(plugin)
        if manifest is None:
            return False
        return permission in manifest.declared_permissions

    def can_access_credentials(self, plugin: str | PluginManifest) -> bool:
        """Credentials are off by default: only a declared permission grants it."""
        return self.check_permission(plugin, CREDENTIAL_PERMISSION)

    def require_permission(self, plugin: str | PluginManifest, permission: str) -> None:
        if not self.check_permission(plugin, permission):
            pid = self._resolve_id(plugin)
            raise PluginError(f"plugin {pid!r} lacks declared permission: {permission}")

    # -- crash isolation ------------------------------------------------------

    def safe_call(
        self,
        plugin: str | PluginManifest,
        fn: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> tuple[bool, Any]:
        """Invoke ``fn`` for a plugin, isolating any failure (PRD 34).

        Returns ``(ok, result)``. On exception the plugin is marked degraded and
        disabled, and ``(False, None)`` is returned -- the host keeps running.
        """
        pid = self._resolve_id(plugin)
        try:
            return True, fn(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001 -- deliberate isolation boundary
            self._save_state(
                pid, PluginState(enabled=False, degraded=True, last_error=str(exc))
            )
            return False, None

    def recover(self, plugin: str | PluginManifest) -> None:
        """Clear a degraded marker and re-enable after the user retries."""
        self.enable(plugin)
