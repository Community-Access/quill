from __future__ import annotations

import importlib.metadata
import re
import tomllib
from collections.abc import Iterable
from pathlib import Path

_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+")
_PROJECT_URL_PREFERENCE = ("homepage", "source", "repository", "documentation")


class ComplianceConfigError(ValueError):
    """Raised when a project metadata file (``pyproject.toml``) cannot be parsed."""


def _load_pyproject(path: Path) -> dict[str, object]:
    """Parse ``pyproject.toml`` at ``path``, surfacing a clear error on corruption.

    A missing file still raises :class:`FileNotFoundError` so callers can detect
    absence, but a syntactically corrupt file raises :class:`ComplianceConfigError`
    that names the offending path instead of leaking a bare ``TOMLDecodeError``.
    """
    try:
        with path.open("rb") as handle:
            return tomllib.load(handle)
    except tomllib.TOMLDecodeError as exc:
        raise ComplianceConfigError(f"Could not parse project metadata file {path}: {exc}") from exc


_DEPENDENCY_METADATA_OVERRIDES: dict[str, tuple[str, str]] = {
    "certifi": ("MPL-2.0", "https://github.com/certifi/python-certifi"),
    "hatchling": ("MIT", "https://github.com/pypa/hatch"),
    "html_to_text": ("MIT", "https://github.com/accessibleapps/html_to_text"),
    "keynote-parser": ("MIT", "https://pypi.org/project/keynote-parser/"),
    "llama-cpp-python": ("MIT", "https://github.com/abetlen/llama-cpp-python"),
    "markitdown": ("MIT", "https://github.com/microsoft/markitdown"),
    "mypy": ("MIT", "https://github.com/python/mypy"),
    "prismatoid": ("MIT", "https://pypi.org/project/prismatoid/"),
    "pyenchant": ("LGPL-2.1-or-later", "https://github.com/pyenchant/pyenchant"),
    "pyobjc": ("MIT", "https://pyobjc.readthedocs.io/"),
    "py2app": ("MIT", "https://py2app.readthedocs.io/"),
    "pytest": ("MIT", "https://github.com/pytest-dev/pytest"),
    "pytest-timeout": ("MIT", "https://github.com/pytest-dev/pytest-timeout"),
    "pytest-xdist": ("MIT", "https://github.com/pytest-dev/pytest-xdist"),
    "pyttsx3": ("MPL-2.0", "https://github.com/nateshmbhat/pyttsx3"),
    "regex": ("Apache-2.0 AND CNRI-Python", "https://github.com/mrabarnett/mrab-regex"),
    "ruff": ("MIT", "https://github.com/astral-sh/ruff"),
    "speechrecognition": ("BSD-3-Clause", "https://github.com/Uberi/speech_recognition"),
    "wx-accessible-webview": ("MIT", "https://github.com/Community-Access/wx-accessible-webview"),
    "wxpython": ("wxWindows", "https://www.wxpython.org/"),
}

_DEPENDENCY_USAGE_NOTES: dict[str, str] = {
    "certifi": "Trusted CA bundle for HTTPS verification.",
    "hatchling": "Build backend used for packaging metadata.",
    "html_to_text": (
        "Converts HTML from clipboard pastes to clean plain text"
        " while preserving document structure (AccessibleApps, MIT)."
    ),
    "keynote-parser": "Apple Keynote parsing for import workflows.",
    "llama-cpp-python": "Python bridge for on-device llama.cpp inference.",
    "markitdown": "Document conversion/import pipeline.",
    "mypy": "Static type checking in CI/dev workflows.",
    "prismatoid": "Screen-reader speech bridge on Windows.",
    "pyenchant": "Spell-check integration.",
    "pyobjc": "macOS bridge bindings for native integration.",
    "py2app": "macOS app packaging support.",
    "pytest": "Test runner.",
    "pytest-timeout": "Per-test timeout protection.",
    "pytest-xdist": "Parallel test execution.",
    "pyttsx3": "System text-to-speech integration.",
    "regex": "Core regular expression engine.",
    "ruff": "Linting and formatting.",
    "speechrecognition": "Speech-recognition helper components.",
    "wx-accessible-webview": "Accessible web preview and dialog surfaces.",
    "wxpython": "Desktop UI framework.",
}

_BUNDLED_COMPONENTS: tuple[dict[str, str], ...] = (
    {
        "name": "WordNet 2.1 (Princeton University)",
        "scope": "bundled-data",
        "version": "2.1",
        "license": "WordNet License",
        "homepage": "https://wordnet.princeton.edu/",
        "source": "quill/data/th_en_US_WordNet_LICENSE.txt",
        "notes": "Bundled lexical database backing thesaurus data.",
    },
    {
        "name": "words_alpha (dwyl/english-words)",
        "scope": "bundled-data",
        "version": "snapshot",
        "license": "Unlicense",
        "homepage": "https://github.com/dwyl/english-words",
        "source": "quill/data/words_alpha.LICENSE.txt",
        "notes": "Bundled English word list.",
    },
    {
        "name": "th_en_US thesaurus dataset",
        "scope": "bundled-data",
        "version": "v2",
        "license": "GPL-2.0-only",
        "homepage": "https://www.gnu.org/licenses/old-licenses/gpl-2.0.html",
        "source": "quill/data/th_en_US_LICENSE.txt",
        "notes": "Bundled thesaurus data license notice.",
    },
    {
        "name": "Piper",
        "scope": "bundled-speech",
        "version": "varies by release",
        "license": "MIT",
        "homepage": "https://github.com/rhasspy/piper",
        "source": "",
        "notes": "Optional bundled speech engine package.",
    },
    {
        "name": "eSpeak NG",
        "scope": "bundled-speech",
        "version": "varies by release",
        "license": "GPL-3.0",
        "homepage": "https://github.com/espeak-ng/espeak-ng",
        "source": "",
        "notes": "Phoneme generation backend used by Piper.",
    },
    {
        "name": "Kokoro",
        "scope": "bundled-speech",
        "version": "82M",
        "license": "Apache-2.0",
        "homepage": "https://huggingface.co/hexgrad/Kokoro-82M",
        "source": "",
        "notes": "Optional neural speech voices.",
    },
    {
        "name": "DECtalk",
        "scope": "bundled-speech",
        "version": "varies by release",
        "license": "Proprietary / redistributable where licensed",
        "homepage": "",
        "source": "",
        "notes": "Optional legacy speech engine package.",
    },
    {
        "name": "Apple Foundation Models",
        "scope": "platform-runtime",
        "version": "OS-provided",
        "license": "Apple platform terms",
        "homepage": "https://developer.apple.com/documentation/foundationmodels",
        "source": "",
        "notes": "On-device AI backend on supported macOS systems.",
    },
    {
        "name": "liblouis",
        "scope": "optional-braille-pack",
        "version": "3.38.0",
        "license": "LGPL-2.1-or-later",
        "homepage": "https://github.com/liblouis/liblouis",
        "source": "",
        "notes": (
            "Open-source braille translation and back-translation library. "
            "Powers the QUILL Braille Pack's UEB, Standard American English, "
            "and international language profiles. "
            "Present only when the optional Braille Pack component is installed. "
            "Copyright (C) the liblouis project contributors."
        ),
    },
)


def normalize_requirement_name(requirement: str) -> str:
    token = requirement.strip()
    match = _NAME_PATTERN.match(token)
    if match is None:
        return token.lower()
    return match.group(0).lower()


def requirement_name(requirement: str) -> str:
    token = requirement.strip()
    match = _NAME_PATTERN.match(token)
    if match is None:
        return token
    return match.group(0)


def requirement_specifier(requirement: str) -> str:
    token = requirement.strip()
    match = _NAME_PATTERN.match(token)
    if match is None:
        return token
    return token[match.end() :].strip() or "(unconstrained)"


def dependency_names_from_pyproject(path: Path, include_optional: bool = True) -> list[str]:
    data = _load_pyproject(path)
    project = data.get("project", {})
    if not isinstance(project, dict):
        return []
    dependencies: list[str] = []
    raw_dependencies = project.get("dependencies", [])
    if isinstance(raw_dependencies, list):
        dependencies.extend(item for item in raw_dependencies if isinstance(item, str))
    if include_optional:
        optional = project.get("optional-dependencies", {})
        if isinstance(optional, dict):
            for values in optional.values():
                if isinstance(values, list):
                    dependencies.extend(item for item in values if isinstance(item, str))
    names = sorted({normalize_requirement_name(item) for item in dependencies if item.strip()})
    return names


def dependency_requirements_from_pyproject(
    path: Path,
    *,
    include_optional: bool = True,
    include_dev: bool = True,
    include_build: bool = True,
) -> list[dict[str, str]]:
    data = _load_pyproject(path)

    rows: dict[str, dict[str, str | set[str]]] = {}

    def add_rows(raw: object, scope: str) -> None:
        if not isinstance(raw, list):
            return
        for item in raw:
            if not isinstance(item, str) or not item.strip():
                continue
            normalized = normalize_requirement_name(item)
            display_name = requirement_name(item)
            row = rows.setdefault(
                normalized,
                {
                    "dependency": normalized,
                    "display_name": display_name or normalized,
                    "scope": set(),
                    "declared": set(),
                },
            )
            scope_set = row["scope"]
            declared_set = row["declared"]
            if isinstance(scope_set, set):
                scope_set.add(scope)
            if isinstance(declared_set, set):
                declared_set.add(item.strip())

    project = data.get("project", {})
    if isinstance(project, dict):
        add_rows(project.get("dependencies", []), "runtime")
        optional = project.get("optional-dependencies", {})
        if include_optional and isinstance(optional, dict):
            for extra_name, values in optional.items():
                if not include_dev and str(extra_name).strip().lower() == "dev":
                    continue
                add_rows(values, f"optional:{extra_name}")

    if include_build:
        build_system = data.get("build-system", {})
        if isinstance(build_system, dict):
            add_rows(build_system.get("requires", []), "build-system")

    output: list[dict[str, str]] = []
    for normalized, row in sorted(rows.items()):
        scopes = sorted(row["scope"]) if isinstance(row["scope"], set) else []
        declared = sorted(row["declared"]) if isinstance(row["declared"], set) else []
        output.append({
            "dependency": normalized,
            "display_name": str(row["display_name"]),
            "scope": ", ".join(scopes),
            "declared": " | ".join(declared),
        })
    return output


def build_dependency_notices(
    path: Path,
    *,
    include_optional: bool = True,
    include_dev: bool = True,
    include_build: bool = True,
) -> list[dict[str, str]]:
    dependencies = dependency_requirements_from_pyproject(
        path,
        include_optional=include_optional,
        include_dev=include_dev,
        include_build=include_build,
    )
    output: list[dict[str, str]] = []
    for row in dependencies:
        dependency = row["dependency"]
        display_name = row["display_name"]
        installed_version, detected_license, homepage = _distribution_metadata(dependency)
        fallback_license, fallback_homepage = _DEPENDENCY_METADATA_OVERRIDES.get(
            dependency,
            ("", ""),
        )
        license_name = detected_license or fallback_license or "UNKNOWN"
        source_url = homepage or fallback_homepage
        version = installed_version
        if version == "unknown":
            declared = row["declared"]
            version = f"not-installed ({requirement_specifier(declared.split(' | ')[0])})"
        output.append({
            "name": display_name,
            "dependency": dependency,
            "scope": row["scope"],
            "declared": row["declared"],
            "version": version,
            "license": license_name,
            "homepage": source_url,
            "notes": _DEPENDENCY_USAGE_NOTES.get(dependency, ""),
        })
    return output


def bundled_component_notices() -> list[dict[str, str]]:
    return [dict(item) for item in _BUNDLED_COMPONENTS]


def render_dependency_notice_table(rows: Iterable[dict[str, str]]) -> str:
    lines = [
        "| Dependency | Scope | Version | License | Link | Declared requirement |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        link = row["homepage"]
        if link:
            link_md = f"[upstream]({link})"
        else:
            link_md = "—"
        lines.append(
            "| "
            + " | ".join([
                _escape_table_cell(row["name"]),
                _escape_table_cell(row["scope"]),
                _escape_table_cell(row["version"]),
                _escape_table_cell(row["license"], max_length=48),
                _escape_table_cell(link_md),
                _escape_table_cell(row["declared"]),
            ])
            + " |"
        )
    return "\n".join(lines)


def render_bundled_component_table(rows: Iterable[dict[str, str]]) -> str:
    lines = [
        "| Component | Scope | Version | License | Link | License source |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        link = row["homepage"]
        if link:
            link_md = f"[upstream]({link})"
        else:
            link_md = "—"
        source_path = row["source"] or "—"
        lines.append(
            "| "
            + " | ".join([
                _escape_table_cell(row["name"]),
                _escape_table_cell(row["scope"]),
                _escape_table_cell(row["version"]),
                _escape_table_cell(row["license"], max_length=48),
                _escape_table_cell(link_md),
                _escape_table_cell(source_path),
            ])
            + " |"
        )
    return "\n".join(lines)


def evaluate_license_gate(
    dependency_licenses: dict[str, str],
    allowed_licenses: set[str],
) -> list[str]:
    violations: list[str] = []
    for dependency, license_name in sorted(dependency_licenses.items()):
        normalized = license_name.strip()
        if not normalized or normalized not in allowed_licenses:
            violations.append(dependency)
    return violations


def render_third_party_notices(dependency_licenses: dict[str, str]) -> str:
    lines = ["Third-Party Notices", ""]
    if not dependency_licenses:
        lines.append("No third-party dependencies were declared.")
        return "\n".join(lines) + "\n"
    lines.append("| Dependency | License |")
    lines.append("| --- | --- |")
    for dependency, license_name in sorted(dependency_licenses.items()):
        lines.append(f"| {dependency} | {license_name or 'UNKNOWN'} |")
    lines.append("")
    return "\n".join(lines)


def render_full_third_party_notices(pyproject_path: Path, project_root: Path) -> str:
    dependency_rows = build_dependency_notices(
        pyproject_path,
        include_optional=True,
        include_dev=True,
        include_build=True,
    )
    bundled_rows = bundled_component_notices()
    lines = [
        "# Third-Party Notices",
        "",
        "This file is generated from declared project metadata "
        "and installed package metadata where available.",
        "",
        "## Declared dependencies",
        "",
        render_dependency_notice_table(dependency_rows),
        "",
        "## Bundled components and data sources",
        "",
        render_bundled_component_table(bundled_rows),
        "",
    ]
    license_texts = _load_local_license_texts(project_root, bundled_rows)
    if license_texts:
        lines.append("## Bundled license texts")
        lines.append("")
        for title, text in license_texts:
            lines.append(f"### {title}")
            lines.append("")
            lines.append("```text")
            lines.append(text.rstrip())
            lines.append("```")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _distribution_metadata(normalized_name: str) -> tuple[str, str, str]:
    for candidate in (normalized_name, normalized_name.replace("-", "_")):
        try:
            dist = importlib.metadata.distribution(candidate)
        except importlib.metadata.PackageNotFoundError:
            continue
        version = dist.version or "unknown"
        metadata = dist.metadata
        license_name = (metadata.get("License") or "").strip()
        if not license_name:
            license_name = _license_from_classifiers(metadata.get_all("Classifier") or [])
        homepage = (metadata.get("Home-page") or "").strip()
        if not homepage:
            homepage = _homepage_from_project_urls(metadata.get_all("Project-URL") or [])
        return version, license_name, homepage
    return "unknown", "", ""


def _license_from_classifiers(classifiers: Iterable[str]) -> str:
    for classifier in classifiers:
        if not classifier.startswith("License ::"):
            continue
        parts = [item.strip() for item in classifier.split("::") if item.strip()]
        if parts:
            return parts[-1]
    return ""


def _homepage_from_project_urls(project_urls: Iterable[str]) -> str:
    candidates: dict[str, str] = {}
    for item in project_urls:
        if "," not in item:
            continue
        label, url = item.split(",", 1)
        label_key = label.strip().lower()
        candidates[label_key] = url.strip()
    for preferred in _PROJECT_URL_PREFERENCE:
        if preferred in candidates and candidates[preferred]:
            return candidates[preferred]
    if candidates:
        return next(iter(candidates.values()))
    return ""


def _load_local_license_texts(
    project_root: Path,
    bundled_rows: Iterable[dict[str, str]],
) -> list[tuple[str, str]]:
    output: list[tuple[str, str]] = []
    for row in bundled_rows:
        source = row.get("source", "").strip()
        if not source:
            continue
        path = project_root / source
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        output.append((row["name"], text))
    return output


def _escape_table_cell(text: str, *, max_length: int | None = None) -> str:
    # Collapse all whitespace (a raw newline ends a GFM table row, which is what
    # broke the About dependency table when a package exposes its full license
    # text instead of an SPDX id) and escape pipes. Truncation is opt-in via
    # ``max_length`` and must only be applied to plain-text cells: truncating a
    # cell that carries Markdown (e.g. ``[upstream](url)``) would leave invalid
    # syntax that renders as raw text. The full license text is in Third-Party
    # Notices.
    collapsed = " ".join(str(text).split())
    if max_length is not None and len(collapsed) > max_length:
        collapsed = collapsed[: max_length - 3].rstrip() + "..."
    return collapsed.replace("|", "\\|")
