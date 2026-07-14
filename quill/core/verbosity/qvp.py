"""QUILL Verbosity Pack (.qvp.json) loader, validator, and install flow (§20-§21).

A QVP is a shareable, **data-only** bundle of verbosity templates. Following the
house style (QUILL ships no ``jsonschema`` runtime dependency), this module
validates a pack by hand against the documented format
(``quill/core/schemas/qvp.json``), collecting structured errors rather than
trusting a library. A pack never contains or runs code — there is no ``exec`` /
``eval`` / ``__import__`` path anywhere in this module, which a test asserts.

:func:`install_pack` runs the full §21 install flow (validate JSON → schema →
kind → version → metadata → template ids → namespace collisions → dependencies →
validate templates against known verbs → install → announce) and returns a
:class:`QVPInstallResult` describing what was accepted, what was rejected and
why, any warnings, and the spoken sequence for the screen reader.

Pure and wx-free.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from quill import __version__ as _QUILL_VERSION
from quill.core.verbosity.parser import validate as validate_template
from quill.core.verbosity.registry import VerbRegistry, default_registry

__all__ = [
    "KIND",
    "QVPError",
    "QVPTemplate",
    "QVPPack",
    "QVPInstallResult",
    "parse_pack",
    "load_pack",
    "install_pack",
]

KIND = "quill-verbosity-pack"


class QVPError(ValueError):
    """Raised when a pack is structurally invalid. Carries every problem found."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = list(errors)
        super().__init__("; ".join(errors) if errors else "invalid QVP pack")


@dataclass(frozen=True, slots=True)
class QVPTemplate:
    """One template inside a pack."""

    id: str
    name: str
    applies_to: str
    template: str
    tags: tuple[str, ...] = ()
    preview_text: str = ""
    depends: tuple[str, ...] = ()
    data_order: tuple[str, ...] = ()
    separator: str = ", "
    speech_template: str = ""
    braille_template: str = ""
    visual_template: str = ""
    sound_event: str = ""


@dataclass(frozen=True, slots=True)
class QVPPack:
    """A parsed, validated verbosity pack."""

    schema_version: str
    kind: str
    min_quill_version: str
    name: str
    author: str
    description: str
    version: str
    license: str
    templates: tuple[QVPTemplate, ...]
    depends: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class QVPInstallResult:
    """The outcome of an install attempt."""

    pack: QVPPack | None
    ok: bool
    accepted: tuple[QVPTemplate, ...] = ()
    rejected_templates: tuple[tuple[str, str], ...] = ()  # (template id, reason)
    warnings: tuple[str, ...] = ()
    spoken_sequence: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()


def _str_field(obj: dict[str, Any], key: str, label: str, errors: list[str]) -> str:
    value = obj.get(key)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{label}: '{key}' is required and must be a non-empty string")
        return ""
    return value


def _str_tuple(obj: dict[str, Any], key: str) -> tuple[str, ...]:
    value = obj.get(key)
    if not isinstance(value, list):
        return ()
    return tuple(str(item) for item in value)


def _parse_template(raw: Any, index: int, errors: list[str]) -> QVPTemplate | None:
    label = f"templates[{index}]"
    if not isinstance(raw, dict):
        errors.append(f"{label}: must be an object")
        return None
    template_id = _str_field(raw, "id", label, errors)
    name = _str_field(raw, "name", label, errors)
    applies_to = _str_field(raw, "applies_to", label, errors)
    template = raw.get("template")
    if not isinstance(template, str):
        errors.append(f"{label}: 'template' is required and must be a string")
        template = ""
    if not template_id:
        return None
    return QVPTemplate(
        id=template_id,
        name=name,
        applies_to=applies_to,
        template=template,
        tags=_str_tuple(raw, "tags"),
        preview_text=str(raw.get("preview_text", "")),
        depends=_str_tuple(raw, "depends"),
        data_order=_str_tuple(raw, "data_order"),
        separator=str(raw.get("separator", ", ")),
        speech_template=str(raw.get("speech_template", "")),
        braille_template=str(raw.get("braille_template", "")),
        visual_template=str(raw.get("visual_template", "")),
        sound_event=str(raw.get("sound_event", "")),
    )


def parse_pack(data: Any) -> QVPPack:
    """Validate ``data`` (already JSON-parsed) and return a :class:`QVPPack`.

    Raises :class:`QVPError` with every problem found. No pack content is ever
    executed — only typed fields are read.
    """
    errors: list[str] = []
    if not isinstance(data, dict):
        raise QVPError(["pack file must be a JSON object"])

    schema_version = _str_field(data, "schema_version", "pack", errors)
    kind = data.get("kind")
    if kind != KIND:
        errors.append(f"pack: 'kind' must equal '{KIND}'")
    min_version = _str_field(data, "min_quill_version", "pack", errors)

    meta = data.get("pack")
    name = author = description = version = license_ = ""
    pack_depends: tuple[str, ...] = ()
    if not isinstance(meta, dict):
        errors.append("pack: 'pack' metadata object is required")
    else:
        name = _str_field(meta, "name", "pack.pack", errors)
        author = _str_field(meta, "author", "pack.pack", errors)
        description = str(meta.get("description", ""))
        version = _str_field(meta, "version", "pack.pack", errors)
        license_ = _str_field(meta, "license", "pack.pack", errors)
        pack_depends = _str_tuple(meta, "depends")

    raw_templates = data.get("templates")
    templates: list[QVPTemplate] = []
    if not isinstance(raw_templates, list) or not raw_templates:
        errors.append("pack: 'templates' must be a non-empty array")
    else:
        for index, raw in enumerate(raw_templates):
            parsed = _parse_template(raw, index, errors)
            if parsed is not None:
                templates.append(parsed)
        ids = [tpl.id for tpl in templates]
        if len(ids) != len(set(ids)):
            errors.append("pack: template ids must be unique within the pack")

    if errors:
        raise QVPError(errors)
    return QVPPack(
        schema_version=schema_version,
        kind=KIND,
        min_quill_version=min_version,
        name=name,
        author=author,
        description=description,
        version=version,
        license=license_,
        templates=tuple(templates),
        depends=pack_depends,
    )


def load_pack(text: str) -> QVPPack:
    """Parse ``text`` as JSON and validate it as a pack."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError as error:
        raise QVPError([f"not valid JSON: {error}"]) from error
    return parse_pack(data)


def _version_tuple(version: str) -> tuple[int, ...]:
    parts: list[int] = []
    for chunk in version.strip().split("."):
        number = ""
        for char in chunk:
            if char.isdigit():
                number += char
            else:
                break
        parts.append(int(number) if number else 0)
    return tuple(parts)


def _version_at_least(have: str, need: str) -> bool:
    """True when ``have`` >= ``need`` under dotted-numeric comparison."""
    have_t = _version_tuple(have)
    need_t = _version_tuple(need)
    length = max(len(have_t), len(need_t))
    have_t += (0,) * (length - len(have_t))
    need_t += (0,) * (length - len(need_t))
    return have_t >= need_t


def install_pack(
    data: Any,
    *,
    current_version: str = _QUILL_VERSION,
    installed_template_ids: tuple[str, ...] = (),
    available_packs: tuple[str, ...] = (),
    registry: VerbRegistry | None = None,
) -> QVPInstallResult:
    """Run the §21 install flow and return a :class:`QVPInstallResult`.

    ``data`` may be a JSON string or an already-parsed object. Validation never
    executes pack content. Templates whose verb is unknown or whose body fails
    validation are rejected with a reason; the rest are accepted. A pack whose
    ``min_quill_version`` exceeds ``current_version`` is rejected wholesale.
    """
    spoken: list[str] = ["Validating pack."]

    # Steps 2-7: JSON + schema + kind + metadata + template ids.
    try:
        pack = load_pack(data) if isinstance(data, str) else parse_pack(data)
    except QVPError as error:
        spoken.append("Pack is not valid and was not installed.")
        return QVPInstallResult(
            pack=None, ok=False, errors=tuple(error.errors), spoken_sequence=tuple(spoken)
        )

    # Step 5: minimum version gate.
    if not _version_at_least(current_version, pack.min_quill_version):
        spoken.append(
            f"Minimum QUILL version {pack.min_quill_version}, you have {current_version}. "
            "Cannot install."
        )
        return QVPInstallResult(
            pack=pack,
            ok=False,
            errors=(f"requires QUILL {pack.min_quill_version}; this is {current_version}",),
            spoken_sequence=tuple(spoken),
        )
    spoken.append(
        f"Minimum QUILL version {pack.min_quill_version}, you have {current_version}. OK."
    )

    warnings: list[str] = []
    registry = registry or default_registry()
    existing = set(installed_template_ids)
    available = set(available_packs)

    # Step 9: dependency resolution (missing deps warn; the UI offers proceed).
    for dependency in pack.depends:
        if dependency not in available:
            warnings.append(f"This pack depends on {dependency}, which is not installed.")

    # Steps 8 + 10: namespace collisions and validate templates against verbs.
    accepted: list[QVPTemplate] = []
    rejected: list[tuple[str, str]] = []
    for tpl in pack.templates:
        if tpl.id in existing:
            rejected.append((tpl.id, "a template with this id is already installed"))
            continue
        verb = registry.get(tpl.applies_to)
        if verb is None:
            rejected.append((tpl.id, f"unknown verb '{tpl.applies_to}'"))
            continue
        report = validate_template(tpl.template, verb)
        if not report.ok:
            reason = report.errors[0].message if report.errors else "invalid template"
            rejected.append((tpl.id, reason))
            continue
        accepted.append(tpl)

    # Step 12: announce.
    added = len(accepted)
    spoken.append(
        f"Pack installed. {added} template{'s' if added != 1 else ''} added. Author: {pack.author}."
    )
    if rejected:
        spoken.append(f"{len(rejected)} template{'s' if len(rejected) != 1 else ''} skipped.")

    return QVPInstallResult(
        pack=pack,
        ok=bool(accepted) or not pack.templates,
        accepted=tuple(accepted),
        rejected_templates=tuple(rejected),
        warnings=tuple(warnings),
        spoken_sequence=tuple(spoken),
    )
