"""Portable, privacy-safe profile and backup package format (SHARE-3).

This module defines the on-disk package that the Export/Back Up (SHARE-1) and
Import/Restore (SHARE-2) dialogs read and write. Two kinds exist:

* ``profile`` (``.quillprofile``) - a portable, privacy-scrubbed package meant
  to hand to a friend.
* ``backup`` (``.quillbackup``) - a full personal restore point for this device.

The privacy boundary is structural, not cosmetic. Every section is classified as
shareable or private; the writer *refuses* to emit a private section (or a
private field inside an otherwise-shareable section such as per-device paths)
into a profile package, and the reader strips any that a hand-edited file might
carry. A round-trip test and a privacy test enforce this.

No ``wx`` imports: this is pure model code consumed by the SHARE dialogs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from quill.core.error_codes import CodedError
from quill.core.storage import read_json, write_json_atomic

#: Bump when the package document shape changes incompatibly.
SCHEMA_VERSION = 1

KIND_PROFILE = "profile"
KIND_BACKUP = "backup"
_KINDS = frozenset({KIND_PROFILE, KIND_BACKUP})

PROFILE_EXTENSION = ".quillprofile"
BACKUP_EXTENSION = ".quillbackup"

#: Section ids the format understands.
SECTION_SETTINGS = "settings"
SECTION_FEATURES = "features"
SECTION_KEYMAP = "keymap"
SECTION_SNIPPETS = "snippets"
SECTION_MACROS = "macros"
SECTION_WATCH = "watch_profiles"
SECTION_DICTIONARY = "dictionary"
SECTION_STYLE = "style_models"
SECTION_LAYOUT = "ui_layout"
# Private sections - never written into or applied from a profile package.
SECTION_SECRETS = "secrets"
SECTION_LICENSE = "license"
SECTION_RECENTS = "recents"
SECTION_DEVICE = "device_paths"
SECTION_TELEMETRY = "telemetry"


@dataclass(frozen=True, slots=True)
class SectionSpec:
    """One named slice of configuration a package can carry."""

    id: str
    title: str
    summary: str
    private: bool = False


SECTION_SPECS: tuple[SectionSpec, ...] = (
    SectionSpec(SECTION_SETTINGS, "Settings", "Your preferences across every Settings tab."),
    SectionSpec(
        SECTION_FEATURES, "Features and profile", "Which features are on and your profile."
    ),
    SectionSpec(SECTION_KEYMAP, "Keyboard map", "Custom shortcuts and the active keyboard pack."),
    SectionSpec(SECTION_SNIPPETS, "Snippets", "Your saved text snippets and triggers."),
    SectionSpec(SECTION_MACROS, "Macros", "Recorded editor macros."),
    SectionSpec(SECTION_WATCH, "Watch profiles", "Watched-folder automation profiles."),
    SectionSpec(SECTION_DICTIONARY, "Dictionary", "Words you added to the spell-check dictionary."),
    SectionSpec(SECTION_STYLE, "Style models", "Learned writing-style models."),
    SectionSpec(SECTION_LAYOUT, "Window layout", "Status bar layout and window arrangement."),
    SectionSpec(
        SECTION_SECRETS,
        "Secrets",
        "API keys and stored credentials. Private; never shared.",
        private=True,
    ),
    SectionSpec(
        SECTION_LICENSE,
        "License",
        "License and registration details. Private; never shared.",
        private=True,
    ),
    SectionSpec(
        SECTION_RECENTS,
        "Recent files",
        "Recently opened files and folders. Private; never shared.",
        private=True,
    ),
    SectionSpec(
        SECTION_DEVICE,
        "Device paths",
        "Paths specific to this computer. Private; never shared.",
        private=True,
    ),
    SectionSpec(
        SECTION_TELEMETRY,
        "Telemetry ids",
        "Anonymous device identifiers. Private; never shared.",
        private=True,
    ),
)

_SPECS_BY_ID: dict[str, SectionSpec] = {spec.id: spec for spec in SECTION_SPECS}

SHAREABLE_SECTION_IDS: frozenset[str] = frozenset(
    spec.id for spec in SECTION_SPECS if not spec.private
)
PRIVATE_SECTION_IDS: frozenset[str] = frozenset(spec.id for spec in SECTION_SPECS if spec.private)

#: Per-device path / device-state fields inside the otherwise-shareable
#: ``settings`` section. These are scrubbed out of a profile package because
#: they only make sense on the machine that wrote them.
PRIVATE_SETTINGS_FIELDS: frozenset[str] = frozenset({
    "read_aloud_dectalk_executable",
    "read_aloud_dectalk_dictionary",
    "read_aloud_piper_executable",
    "read_aloud_piper_model",
    "read_aloud_piper_model_dir",
    "read_aloud_espeak_executable",
    "watch_folder_path",
    "last_update_check",
    "skipped_update_version",
})


class PackageError(CodedError):
    """A package document is malformed or names an unknown section."""

    code = "QUILL-SHARE-PACKAGE-MALFORMED"


class PrivacyError(PackageError):
    """An attempt was made to put a private section into a profile package."""


def section_spec(section_id: str) -> SectionSpec | None:
    """Return the spec for ``section_id`` or ``None`` when it is unknown."""
    return _SPECS_BY_ID.get(section_id)


def extension_for_kind(kind: str) -> str:
    """Return the file extension a package of ``kind`` should use."""
    return PROFILE_EXTENSION if kind == KIND_PROFILE else BACKUP_EXTENSION


def scrub_settings_for_profile(payload: Any) -> Any:
    """Return a copy of a settings-section payload with private fields removed.

    Handles both the wrapped ``{"schema_version", "settings": {...}}`` export
    shape and a bare settings mapping. Non-mappings are returned unchanged.
    """
    if not isinstance(payload, dict):
        return payload
    if isinstance(payload.get("settings"), dict):
        inner = {
            key: value
            for key, value in payload["settings"].items()
            if key not in PRIVATE_SETTINGS_FIELDS
        }
        scrubbed = dict(payload)
        scrubbed["settings"] = inner
        return scrubbed
    return {key: value for key, value in payload.items() if key not in PRIVATE_SETTINGS_FIELDS}


def _scrub_section_for_profile(section_id: str, payload: Any) -> Any:
    if section_id == SECTION_SETTINGS:
        return scrub_settings_for_profile(payload)
    return payload


@dataclass(frozen=True, slots=True)
class Package:
    """A validated package ready to inspect or apply."""

    kind: str
    name: str
    source_version: str
    created: str
    sections: dict[str, Any]
    warnings: list[str] = field(default_factory=list)

    @property
    def is_profile(self) -> bool:
        return self.kind == KIND_PROFILE


def build_package(
    *,
    kind: str,
    name: str,
    source_version: str,
    sections: dict[str, Any],
    created: str | None = None,
) -> dict[str, Any]:
    """Assemble a package document from ``sections``.

    For a ``profile`` kind, any private section raises :class:`PrivacyError`
    and the settings section is scrubbed of per-device fields, so the writer
    can never leak a secret, recent path, or license field into a profile.
    """
    if kind not in _KINDS:
        raise PackageError(f"Unknown package kind {kind!r}.")
    selected: dict[str, Any] = {}
    for section_id, payload in sections.items():
        spec = _SPECS_BY_ID.get(section_id)
        if spec is None:
            raise PackageError(f"Unknown section {section_id!r}.")
        if kind == KIND_PROFILE:
            if spec.private:
                raise PrivacyError(
                    f"Section {section_id!r} is private and cannot be shared in a profile."
                )
            payload = _scrub_section_for_profile(section_id, payload)
        selected[section_id] = payload
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "kind": kind,
        "name": str(name).strip() or _default_name(kind),
        "source_version": str(source_version),
        "created": created or datetime.now(UTC).isoformat(timespec="seconds"),
        "contents": sorted(selected),
    }
    return {"manifest": manifest, "sections": selected}


def _default_name(kind: str) -> str:
    return "Shared profile" if kind == KIND_PROFILE else "Full backup"


def read_package(raw: object) -> Package:
    """Validate a package document and return a typed :class:`Package`.

    A ``profile`` package is defensively cleansed: any private section that a
    hand-edited file carries is dropped (with a warning) and the settings
    section is re-scrubbed, so private data from a profile can never be applied.
    """
    if not isinstance(raw, dict):
        raise PackageError("Package must be a JSON object.")
    manifest = raw.get("manifest")
    if not isinstance(manifest, dict):
        raise PackageError("Package is missing its manifest.")
    if int(manifest.get("schema_version", 0)) != SCHEMA_VERSION:
        raise PackageError("Unsupported package schema version.")
    kind = str(manifest.get("kind", ""))
    if kind not in _KINDS:
        raise PackageError(f"Unknown package kind {kind!r}.")
    sections_raw = raw.get("sections")
    if not isinstance(sections_raw, dict):
        raise PackageError("Package is missing its sections.")
    warnings: list[str] = []
    sections: dict[str, Any] = {}
    for section_id, payload in sections_raw.items():
        spec = _SPECS_BY_ID.get(str(section_id))
        if spec is None:
            warnings.append(f"Ignored unknown section {section_id!r}.")
            continue
        if kind == KIND_PROFILE and spec.private:
            warnings.append(f"Stripped private section {section_id!r} from profile.")
            continue
        if kind == KIND_PROFILE:
            payload = _scrub_section_for_profile(str(section_id), payload)
        sections[str(section_id)] = payload
    return Package(
        kind=kind,
        name=str(manifest.get("name", _default_name(kind))),
        source_version=str(manifest.get("source_version", "")),
        created=str(manifest.get("created", "")),
        sections=sections,
        warnings=warnings,
    )


def private_fields_present(document: object) -> list[str]:
    """Return any private section ids or private settings fields in a package.

    Used by the privacy test: for a correctly built profile this is empty. The
    check inspects the raw document (not a :class:`Package`) so it catches
    leaks before any cleansing.
    """
    offenders: list[str] = []
    if not isinstance(document, dict):
        return offenders
    sections = document.get("sections")
    if not isinstance(sections, dict):
        return offenders
    for section_id, payload in sections.items():
        if str(section_id) in PRIVATE_SECTION_IDS:
            offenders.append(str(section_id))
        if str(section_id) == SECTION_SETTINGS:
            inner = payload.get("settings") if isinstance(payload, dict) else None
            candidate = inner if isinstance(inner, dict) else payload
            if isinstance(candidate, dict):
                for key in candidate:
                    if key in PRIVATE_SETTINGS_FIELDS:
                        offenders.append(f"{SECTION_SETTINGS}.{key}")
    return offenders


def package_summary(package: Package) -> str:
    """Return a plain-language, read-aloud-friendly summary of a package."""
    kind_word = "shareable profile" if package.is_profile else "full backup"
    lines = [
        f"{package.name}: a {kind_word} from QUILL {package.source_version or 'unknown'}.",
    ]
    if package.created:
        lines.append(f"Created {package.created}.")
    if package.sections:
        lines.append("What's inside:")
        for section_id in sorted(package.sections):
            spec = _SPECS_BY_ID.get(section_id)
            title = spec.title if spec else section_id
            summary = spec.summary if spec else ""
            lines.append(f"- {title}: {summary}".rstrip(": ").rstrip())
    else:
        lines.append("This package contains no applicable sections.")
    if package.is_profile:
        lines.append("Private data (secrets, recent files, device paths) is never included.")
    if package.warnings:
        lines.append("Notes: " + " ".join(package.warnings))
    return "\n".join(lines)


def write_package_file(document: dict[str, Any], path: Path) -> None:
    """Atomically write a package document to ``path``."""
    write_json_atomic(path, document)


def read_package_file(path: Path) -> Package:
    """Read and validate a package file from ``path``."""
    raw = read_json(path, default=None)
    if raw is None:
        raise PackageError(f"Package file not found or empty: {path}")
    return read_package(raw)
