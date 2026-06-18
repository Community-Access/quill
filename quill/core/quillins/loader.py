"""Discovery and enable/disable state for installed Quillins.

Installed Quillins live under ``%APPDATA%\\Quill\\extensions\\<id>\\`` with a
``manifest.json`` at the root of each. Per-extension enablement and granted
capabilities are recorded in ``extensions\\state.json``, written atomically and
schema-validated like every other QUILL store.

**SEC-8 gate (non-negotiable for 1.0).** Third-party discovery returns nothing
unless the ``core.third_party_plugins`` feature flag is enabled, and that flag is
``locked_off`` for QUILL 1.0. A default build therefore never discovers, loads,
or runs third-party Quillin code. The gate is shared with :mod:`quill.plugins`
so there is a single source of truth.

**Bundled Quillins (Tier C).** QUILL's own features shipped as Quillins live
under ``quill/quillins_bundled/<id>/`` *inside the install tree* (never the
per-user ``%APPDATA%`` root). They are discovered by the separate
:func:`discover_bundled_extensions` path, ship **enabled**, and are gated by the
on-by-default ``core.bundled_quillins`` flag — wholly independent of the SEC-8
third-party lock. They still declare capabilities and still hit the runtime
consent gate for ``fs.*``/``net``; the non-consent capabilities they declare are
pre-granted so a trusted shipped feature does not nag on first use.

This module imports no ``wx`` and no platform code.
"""

from __future__ import annotations

import ast
import json
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from quill.core.paths import app_data_dir
from quill.core.quillins.model import (
    CONSENT_GATED_CAPABILITIES,
    ExtensionManifest,
)
from quill.core.quillins.validation import parse_manifest
from quill.core.storage import read_json, write_json_atomic
from quill.plugins import third_party_plugins_enabled

_SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)")


def _parse_semver(version: str) -> tuple[int, int, int] | None:
    match = _SEMVER_RE.match(version.strip())
    if not match:
        return None
    return (int(match.group(1)), int(match.group(2)), int(match.group(3)))


def _running_quill_version() -> str:
    try:
        from quill import __version__  # noqa: PLC0415

        return __version__ or "0.0.0"
    except ImportError:
        return "0.0.0"


def _check_min_version_error(manifest: ExtensionManifest) -> str | None:
    """Return an error string if the Quillin requires a newer QUILL version, else None."""
    if not manifest.min_quill_version:
        return None
    required = _parse_semver(manifest.min_quill_version)
    running = _parse_semver(_running_quill_version())
    if required is None or running is None:
        return None
    if running < required:
        return (
            f"requires QUILL {manifest.min_quill_version} "
            f"(running {_running_quill_version()}); update QUILL to enable this Quillin"
        )
    return None


def _check_requires_errors(
    manifest: ExtensionManifest,
    available: dict[str, str],
) -> tuple[str, ...]:
    """Return error strings for unmet ``requires`` declarations.

    ``available`` maps extension id -> version string for every manifest that
    was successfully parsed in this discovery pass (whether enabled or not).
    A dependency is satisfied when it is present and its version meets
    ``min_version`` (if specified).
    """
    errors: list[str] = []
    for dep in manifest.requires:
        dep_version = available.get(dep.id)
        if dep_version is None:
            errors.append(f"requires Quillin '{dep.id}' which is not installed")
            continue
        if dep.min_version:
            req = _parse_semver(dep.min_version)
            have = _parse_semver(dep_version)
            if req is not None and have is not None and have < req:
                errors.append(
                    f"requires Quillin '{dep.id}' >= {dep.min_version} (installed: {dep_version})"
                )
    return tuple(errors)


STATE_SCHEMA_VERSION = 1
_MANIFEST_FILENAME = "manifest.json"
_STATE_FILENAME = "state.json"

#: Feature flag gating the bundled (Tier C) Quillin path. On by default; entirely
#: separate from the SEC-8 ``core.third_party_plugins`` lock.
BUNDLED_QUILLINS_FEATURE = "core.bundled_quillins"


@dataclass(frozen=True, slots=True)
class InstalledExtension:
    """A Quillin found on disk, valid or not."""

    id: str
    directory: Path
    manifest: ExtensionManifest | None
    enabled: bool
    granted_capabilities: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

    @property
    def is_valid(self) -> bool:
        return self.manifest is not None and not self.errors


@dataclass(slots=True)
class _ExtensionStateEntry:
    enabled: bool = False
    granted_capabilities: tuple[str, ...] = ()
    # Events the user has explicitly disabled for this Quillin. Checked
    # at dispatch time; ``enabled_by_default: false`` starts events here.
    disabled_events: frozenset[str] = field(default_factory=frozenset)


@dataclass(slots=True)
class ExtensionState:
    """Per-extension enablement and granted capabilities."""

    entries: dict[str, _ExtensionStateEntry] = field(default_factory=dict)

    def entry(self, extension_id: str) -> _ExtensionStateEntry:
        return self.entries.get(extension_id, _ExtensionStateEntry())

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": STATE_SCHEMA_VERSION,
            "extensions": {
                extension_id: {
                    "enabled": entry.enabled,
                    "granted_capabilities": list(entry.granted_capabilities),
                    "disabled_events": sorted(entry.disabled_events),
                }
                for extension_id, entry in sorted(self.entries.items())
            },
        }


def extensions_root(*, root: Path | None = None) -> Path:
    """Return the directory that holds installed Quillins."""

    base = root if root is not None else app_data_dir()
    return base / "extensions"


def _state_path(*, root: Path | None = None) -> Path:
    return extensions_root(root=root) / _STATE_FILENAME


def load_state(*, root: Path | None = None) -> ExtensionState:
    """Read the enablement state store, tolerating a missing or partial file."""

    raw = read_json(_state_path(root=root), default=None)
    state = ExtensionState()
    if not isinstance(raw, dict):
        return state
    extensions = raw.get("extensions")
    if not isinstance(extensions, dict):
        return state
    for extension_id, value in extensions.items():
        if not isinstance(extension_id, str) or not isinstance(value, dict):
            continue
        enabled = bool(value.get("enabled", False))
        raw_caps = value.get("granted_capabilities", [])
        caps = (
            tuple(item for item in raw_caps if isinstance(item, str))
            if isinstance(raw_caps, list)
            else ()
        )
        raw_disabled = value.get("disabled_events", [])
        disabled_events = (
            frozenset(item for item in raw_disabled if isinstance(item, str))
            if isinstance(raw_disabled, list)
            else frozenset()
        )
        state.entries[extension_id] = _ExtensionStateEntry(
            enabled=enabled,
            granted_capabilities=caps,
            disabled_events=disabled_events,
        )
    return state


def save_state(state: ExtensionState, *, root: Path | None = None) -> None:
    """Persist the enablement state store atomically."""

    base = root if root is not None else app_data_dir()
    write_json_atomic(_state_path(root=root), state.to_dict(), base=base)


def _check_main_has_register(directory: Path, manifest: ExtensionManifest) -> str | None:
    """Return an error string if the main module lacks a top-level register() function.

    Layer 1 Quillins (``main`` is ``None``) are exempt — they contribute only
    static metadata and run no Python code.
    """
    if manifest.main is None:
        return None
    main_path = (directory / manifest.main).resolve()
    if not main_path.exists():
        return f"main module '{manifest.main}' not found"
    try:
        source = main_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(main_path))
    except (OSError, SyntaxError) as error:
        return f"cannot parse main module: {error}"
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "register":
            return None
    return "main module defines no register(api) function"


def _read_manifest(directory: Path) -> tuple[ExtensionManifest | None, tuple[str, ...]]:
    manifest_path = directory / _MANIFEST_FILENAME
    if not manifest_path.exists():
        return None, (f"missing {_MANIFEST_FILENAME}",)
    try:
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return None, (f"unreadable manifest: {error}",)
    try:
        manifest = parse_manifest(raw)
    except Exception as error:  # ManifestError carries the detailed problem list
        errors = getattr(error, "errors", None)
        if isinstance(errors, list):
            return None, tuple(str(item) for item in errors)
        return None, (str(error),)
    version_error = _check_min_version_error(manifest)
    if version_error:
        return None, (version_error,)
    register_error = _check_main_has_register(directory, manifest)
    if register_error:
        return manifest, (register_error,)
    return manifest, ()


def discover_extensions(features: object, *, root: Path | None = None) -> list[InstalledExtension]:
    """Discover installed Quillins.

    Returns an empty list unless the ``core.third_party_plugins`` flag is enabled
    (SEC-8). Because that flag is ``locked_off`` for 1.0, a default build always
    returns ``[]`` and never reads third-party manifests.
    """

    if not third_party_plugins_enabled(features):
        return []

    directory_root = extensions_root(root=root)
    if not directory_root.exists():
        return []

    state = load_state(root=root)
    discovered: list[InstalledExtension] = []
    for child in sorted(directory_root.iterdir(), key=lambda path: path.name):
        if not child.is_dir():
            continue
        manifest, errors = _read_manifest(child)
        extension_id = manifest.id if manifest is not None else child.name
        entry = state.entry(extension_id)
        discovered.append(
            InstalledExtension(
                id=extension_id,
                directory=child,
                manifest=manifest,
                enabled=entry.enabled,
                granted_capabilities=entry.granted_capabilities,
                errors=errors,
            )
        )

    # Second pass: enforce ``requires`` declarations now that all manifests are known.
    available = {
        item.manifest.id: item.manifest.version for item in discovered if item.manifest is not None
    }
    return [
        InstalledExtension(
            id=item.id,
            directory=item.directory,
            manifest=item.manifest,
            enabled=item.enabled,
            granted_capabilities=item.granted_capabilities,
            errors=item.errors + _check_requires_errors(item.manifest, available)
            if item.manifest is not None
            else item.errors,
        )
        for item in discovered
    ]


def load_enabled_manifests(
    features: object, *, root: Path | None = None
) -> list[ExtensionManifest]:
    """Return validated manifests for enabled, valid Quillins only (SEC-8 gated)."""

    manifests: list[ExtensionManifest] = []
    for installed in discover_extensions(features, root=root):
        if installed.enabled and installed.manifest is not None and installed.is_valid:
            manifests.append(installed.manifest)
    return manifests


def set_enabled(extension_id: str, enabled: bool, *, root: Path | None = None) -> ExtensionState:
    """Enable or disable a Quillin and persist the change."""

    state = load_state(root=root)
    entry = state.entries.get(extension_id, _ExtensionStateEntry())
    entry.enabled = enabled
    state.entries[extension_id] = entry
    save_state(state, root=root)
    return state


def grant_capabilities(
    extension_id: str, capabilities: tuple[str, ...], *, root: Path | None = None
) -> ExtensionState:
    """Record the capabilities a user has granted a Quillin and persist."""

    state = load_state(root=root)
    entry = state.entries.get(extension_id, _ExtensionStateEntry())
    entry.granted_capabilities = tuple(dict.fromkeys(capabilities))
    state.entries[extension_id] = entry
    save_state(state, root=root)
    return state


def set_event_enabled(
    extension_id: str, event_name: str, enabled: bool, *, root: Path | None = None
) -> ExtensionState:
    """Enable or disable a single document event subscription for a Quillin.

    When ``enabled`` is ``False``, the event name is added to
    ``disabled_events`` and the host will skip the handler at dispatch time.
    When ``True``, it is removed (restoring default behaviour).
    """

    state = load_state(root=root)
    entry = state.entries.get(extension_id, _ExtensionStateEntry())
    if enabled:
        entry.disabled_events = entry.disabled_events - {event_name}
    else:
        entry.disabled_events = entry.disabled_events | {event_name}
    state.entries[extension_id] = entry
    save_state(state, root=root)
    return state


def is_event_enabled(extension_id: str, event_name: str, *, root: Path | None = None) -> bool:
    """Return whether a document event subscription is active for a Quillin."""

    state = load_state(root=root)
    entry = state.entry(extension_id)
    return event_name not in entry.disabled_events


def remove_extension(extension_id: str, *, root: Path | None = None) -> bool:
    """Uninstall a Quillin: delete its directory and forget its state.

    Returns ``True`` when a directory was removed. Path containment is enforced
    so a crafted id can never delete outside the extensions root.
    """

    directory_root = extensions_root(root=root).resolve()
    target = (extensions_root(root=root) / extension_id).resolve()
    if directory_root not in target.parents:
        return False

    removed = False
    if target.is_dir():
        shutil.rmtree(target)
        removed = True

    state = load_state(root=root)
    if extension_id in state.entries:
        del state.entries[extension_id]
        save_state(state, root=root)
    return removed


def install_extension(source_dir: Path, *, root: Path | None = None) -> str:
    """Install or update a Quillin by copying its directory into the extensions root.

    ``source_dir`` must contain a valid ``manifest.json``. Returns the extension
    id on success. Raises ``ValueError`` when the manifest is absent or unreadable,
    and ``ManifestError`` when it fails validation.

    Path containment is enforced: the destination is always directly inside
    ``extensions_root()`` — a crafted id cannot install outside it.
    """

    import json as _json

    from quill.core.quillins.model import ManifestError

    manifest_path = source_dir / _MANIFEST_FILENAME
    if not manifest_path.is_file():
        raise ValueError(f"No manifest.json in {source_dir}")
    try:
        raw = _json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, _json.JSONDecodeError) as exc:
        raise ValueError(f"manifest.json unreadable: {exc}") from exc
    if not isinstance(raw, dict) or not isinstance(raw.get("id"), str):
        raise ManifestError(["manifest must have a string 'id' field"])
    extension_id: str = raw["id"]

    dest_root = extensions_root(root=root).resolve()
    dest = (dest_root / extension_id).resolve()
    if dest.parent != dest_root:
        raise ValueError(f"Extension id '{extension_id}' would install outside extensions root")

    dest_root.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(source_dir, dest)
    set_enabled(extension_id, True, root=root)
    return extension_id


# -- Bundled Quillins (Tier C) -------------------------------------------------


def bundled_quillins_enabled(features: object) -> bool:
    """Return whether the bundled (Tier C) Quillin path is active.

    Gated by the on-by-default ``core.bundled_quillins`` flag, *not* the SEC-8
    third-party lock. A ``features`` object without ``is_enabled`` is treated as
    disabled, matching the conservative default used elsewhere.
    """

    is_enabled = getattr(features, "is_enabled", None)
    if not callable(is_enabled):
        return False
    return bool(is_enabled(BUNDLED_QUILLINS_FEATURE))


def bundled_extensions_root(*, root: Path | None = None) -> Path:
    """Return the read-only directory holding QUILL's bundled Quillins.

    Defaults to ``quill/quillins_bundled`` inside the install tree. Tests may
    override ``root`` to point at a fixture directory.
    """

    if root is not None:
        return root
    # quill/core/quillins/loader.py -> parents[2] is the ``quill`` package root.
    return Path(__file__).resolve().parents[2] / "quillins_bundled"


def _bundled_granted_capabilities(manifest: ExtensionManifest) -> tuple[str, ...]:
    """Pre-grant a bundled Quillin's non-consent capabilities.

    Trusted bundled authors get their declared ``editor.*``/``ui.*``/``clipboard.*``
    capabilities up front, so a shipped feature does not prompt on first use.
    ``fs.*``/``net`` are *not* pre-granted here — they remain consent-gated at
    runtime, so the security proof stays real.
    """

    return tuple(
        capability
        for capability in manifest.capabilities
        if capability not in CONSENT_GATED_CAPABILITIES
    )


def discover_bundled_extensions(
    features: object, *, root: Path | None = None
) -> list[InstalledExtension]:
    """Discover QUILL's bundled Quillins (Tier C).

    Returns an empty list unless ``core.bundled_quillins`` is enabled. Each
    bundled Quillin is reported as ``enabled=True`` with its non-consent
    capabilities pre-granted; invalid manifests are surfaced with their errors so
    the Manager can show them.
    """

    if not bundled_quillins_enabled(features):
        return []

    directory_root = bundled_extensions_root(root=root)
    if not directory_root.exists():
        return []

    discovered: list[InstalledExtension] = []
    for child in sorted(directory_root.iterdir(), key=lambda path: path.name):
        if not child.is_dir():
            continue
        manifest, errors = _read_manifest(child)
        extension_id = manifest.id if manifest is not None else child.name
        granted = _bundled_granted_capabilities(manifest) if manifest is not None else ()
        discovered.append(
            InstalledExtension(
                id=extension_id,
                directory=child,
                manifest=manifest,
                enabled=True,
                granted_capabilities=granted,
                errors=errors,
            )
        )

    # Second pass: enforce ``requires`` declarations now that all manifests are known.
    available = {
        item.manifest.id: item.manifest.version for item in discovered if item.manifest is not None
    }
    return [
        InstalledExtension(
            id=item.id,
            directory=item.directory,
            manifest=item.manifest,
            enabled=item.enabled,
            granted_capabilities=item.granted_capabilities,
            errors=item.errors + _check_requires_errors(item.manifest, available)
            if item.manifest is not None
            else item.errors,
        )
        for item in discovered
    ]


def load_enabled_bundled_manifests(
    features: object, *, root: Path | None = None
) -> list[ExtensionManifest]:
    """Return validated manifests for all valid bundled Quillins (flag-gated)."""

    manifests: list[ExtensionManifest] = []
    for installed in discover_bundled_extensions(features, root=root):
        if installed.manifest is not None and installed.is_valid:
            manifests.append(installed.manifest)
    return manifests
