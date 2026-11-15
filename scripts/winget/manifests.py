"""Build and check the QuillVille WinGet multi-file manifest sets.

This module is pure for an already-fetched GitHub release record. It never
submits a manifest or writes outside the output directory supplied by its
caller. The network and GitHub write steps live in separate entry points.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from string import Template
from typing import Any
from urllib.request import Request, urlopen

from quill.core.release_tags import parse_release_tag
from quill.core.versioning import ReleaseVersion

REPO_ROOT = Path(__file__).resolve().parents[2]
WINGET_ROOT = REPO_ROOT / "packaging" / "winget"
TEMPLATE_ROOT = WINGET_ROOT / "templates"
_SHA256 = re.compile(r"^[A-Fa-f0-9]{64}$")
_FORBIDDEN_FIELDS = re.compile(r"(?m)^\s*(?:ProductCode|UpgradeCode):")


@dataclass(frozen=True)
class ManifestDraft:
    app_key: str
    package_id: str
    package_version: str
    release_tag: str
    release_url: str
    asset_name: str
    asset_url: str
    asset_sha256: str
    files: dict[str, str]


def load_catalog(path: Path = WINGET_ROOT / "apps.json") -> dict[str, Any]:
    """Read the reviewed package catalog."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("apps"), dict):
        raise ValueError("WinGet app catalog must be an object with an apps map.")
    return data


def _asset_sha256(asset: dict[str, Any]) -> str:
    digest = str(asset.get("digest", "") or "")
    if digest.lower().startswith("sha256:"):
        value = digest.split(":", 1)[1]
        if _SHA256.fullmatch(value):
            return value.upper()
    url = str(asset.get("browser_download_url", "") or "")
    if not url.startswith("https://github.com/Community-Access/quill/releases/download/"):
        raise ValueError("The installer asset does not have a stable Quill release URL.")
    request = Request(url, headers={"User-Agent": "Quill-WinGet-Manifest"})
    checksum = hashlib.sha256()
    with urlopen(request, timeout=60) as response:  # noqa: S310 - fixed HTTPS publisher host
        while chunk := response.read(1024 * 1024):
            checksum.update(chunk)
    return checksum.hexdigest().upper()


def _render_templates(
    values: dict[str, str], *, template_root: Path = TEMPLATE_ROOT
) -> dict[str, str]:
    result: dict[str, str] = {}
    for template_name, output_suffix in (
        ("version.yaml.template", "version.yaml"),
        ("defaultLocale.yaml.template", "locale.en-US.yaml"),
        ("installer.yaml.template", "installer.yaml"),
    ):
        source = (template_root / template_name).read_text(encoding="utf-8")
        # The schema header is literal: its "$schema" is not a placeholder.
        header, newline, body = source.partition("\n")
        if header.startswith("# yaml-language-server: $schema="):
            result[output_suffix] = header + newline + Template(body).substitute(values)
        else:
            result[output_suffix] = Template(source).substitute(values)
    return result


def _manifest_path(package_id: str, version: str, filename: str) -> str:
    publisher, package = package_id.split(".", 1)
    return (
        f"manifests/{publisher[0].lower()}/{publisher}/{package}/{version}/{package_id}.{filename}"
    )


def build_manifest_draft(
    release: dict[str, Any],
    app_key: str,
    *,
    catalog: dict[str, Any] | None = None,
    template_root: Path = TEMPLATE_ROOT,
) -> ManifestDraft:
    """Render one stable, version-specific installer release for one app."""
    catalog = catalog or load_catalog()
    apps = catalog["apps"]
    app = apps.get(app_key)
    if not isinstance(app, dict):
        raise ValueError(f"No WinGet package metadata is configured for {app_key!r}.")
    if app.get("package_url_verified") is not True:
        raise ValueError(
            f"Confirm the official product page for {app_key!r} before generating manifests."
        )
    package_url = str(app.get("package_url", "") or "")
    if not package_url.startswith("https://"):
        raise ValueError(f"The official product page for {app_key!r} must use HTTPS.")
    if release.get("draft") or release.get("prerelease"):
        raise ValueError("WinGet submissions are limited to published Stable releases.")
    tag = str(release.get("tag_name", "") or "")
    parsed_tag = parse_release_tag(tag)
    if parsed_tag is None or parsed_tag.app_key != app_key:
        raise ValueError(f"Release tag {tag!r} does not identify {app_key!r}.")
    version = ReleaseVersion.parse(parsed_tag.version)
    if version.is_prerelease:
        raise ValueError("WinGet submissions are limited to final, Stable versions.")
    # WinGet follows the Apps & Features version; rebuilds share it.
    package_version = version.plain()
    prefix = str(app.get("setup_prefix", ""))
    asset_name = f"{prefix}{package_version}.exe"
    assets = release.get("assets")
    if not isinstance(assets, list):
        assets = []
    matches = [
        asset
        for asset in assets
        if isinstance(asset, dict) and str(asset.get("name", "")) == asset_name
    ]
    if len(matches) != 1:
        raise ValueError(f"Expected one {asset_name} Stable installer asset; found {len(matches)}.")
    asset = matches[0]
    asset_url = str(asset.get("browser_download_url", "") or "")
    if not asset_url.startswith("https://github.com/Community-Access/quill/releases/download/"):
        raise ValueError("The installer must use a version-specific Community-Access release URL.")
    if tag not in asset_url:
        raise ValueError("The installer URL must name the exact release tag.")
    sha256 = _asset_sha256(asset)
    package_id = str(app["package_id"])
    release_url = str(release.get("html_url", "") or "")
    if not release_url.startswith("https://github.com/Community-Access/quill/releases/tag/"):
        raise ValueError("The Stable release page URL is missing or unexpected.")
    display_name = f"{app['package_name']} {package_version}"
    values = {
        "PackageIdentifier": package_id,
        "PackageVersion": package_version,
        "PackageName": str(app["package_name"]),
        "PackageUrl": package_url,
        "LicenseUrl": f"https://github.com/Community-Access/quill/blob/{tag}/LICENSE",
        "ShortDescription": str(app["short_description"]),
        "Moniker": str(app["moniker"]),
        "Tag": str(app["tag"]),
        "ReleaseNotesUrl": release_url,
        "InstallerUrl": asset_url,
        "InstallerSha256": sha256,
        "AppsAndFeaturesDisplayName": display_name,
    }
    suffixes = _render_templates(values, template_root=template_root)
    files = {
        _manifest_path(package_id, package_version, filename): body
        for filename, body in suffixes.items()
    }
    validate_manifest_files(files, package_id=package_id, package_version=package_version)
    return ManifestDraft(
        app_key=app_key,
        package_id=package_id,
        package_version=package_version,
        release_tag=tag,
        release_url=release_url,
        asset_name=asset_name,
        asset_url=asset_url,
        asset_sha256=sha256,
        files=files,
    )


def validate_manifest_files(
    files: dict[str, str], *, package_id: str, package_version: str
) -> None:
    """Fail closed on mismatched version sets or self-updater safeguards."""
    if len(files) != 3:
        raise ValueError("A WinGet package version must contain exactly three manifest files.")
    joined = "\n".join(files.values())
    if "${" in joined:
        raise ValueError("A rendered WinGet manifest still contains template placeholders.")
    if _FORBIDDEN_FIELDS.search(joined):
        raise ValueError("Inno Setup manifests must not add MSI ProductCode or UpgradeCode fields.")
    for text in files.values():
        if f"PackageIdentifier: {package_id}" not in text:
            raise ValueError("The manifest files do not share the configured package identifier.")
        if f"PackageVersion: {package_version}" not in text:
            raise ValueError("The manifest files do not share the configured package version.")
        if "ManifestVersion: 1.28.0" not in text:
            raise ValueError("Every draft must use the currently documented 1.28.0 schema.")
        if not text.startswith("# yaml-language-server: $schema=https://aka.ms/winget-manifest."):
            raise ValueError("Every manifest file needs its WinGet schema header.")
    installer = next((text for text in files.values() if "ManifestType: installer" in text), "")
    if "RequireExplicitUpgrade: true" not in installer:
        raise ValueError("Self-updating Quill packages must require an explicit WinGet upgrade.")
    if "AppsAndFeaturesEntries:" not in installer or "DisplayName:" not in installer:
        raise ValueError("The installer manifest must match the exact Apps & Features entry.")
    if "InstallerType: inno" not in installer:
        raise ValueError("Quill setup artifacts must be declared as Inno Setup installers.")
    installer_prefix = "InstallerUrl: https://github.com/Community-Access/quill/releases/download/"
    if installer_prefix not in installer:
        raise ValueError("The installer URL must be an official, version-specific release asset.")


def validate_templates(template_root: Path = TEMPLATE_ROOT) -> None:
    """Guard template properties that automatic manifest tools must not erase."""
    expected = {
        "version.yaml.template": "version",
        "defaultLocale.yaml.template": "defaultLocale",
        "installer.yaml.template": "installer",
    }
    for filename, manifest_type in expected.items():
        path = template_root / filename
        if not path.is_file():
            raise ValueError(f"WinGet template is missing: {filename}")
        content = path.read_text(encoding="utf-8")
        if f"ManifestType: {manifest_type}" not in content:
            raise ValueError(f"WinGet template has the wrong ManifestType: {filename}")
        if "ManifestVersion: 1.28.0" not in content:
            raise ValueError(f"WinGet template is not on schema 1.28.0: {filename}")
        schema_header = "# yaml-language-server: $schema=https://aka.ms/winget-manifest."
        if not content.startswith(schema_header):
            raise ValueError(f"WinGet template needs its schema header: {filename}")
    installer = (template_root / "installer.yaml.template").read_text(encoding="utf-8")
    if "RequireExplicitUpgrade: true" not in installer:
        raise ValueError("WinGet installer template lost the explicit-upgrade safeguard.")
    if _FORBIDDEN_FIELDS.search(installer):
        raise ValueError("WinGet installer template must not match Inno packages by MSI codes.")
    if "AppsAndFeaturesEntries:" not in installer:
        raise ValueError("WinGet installer template must match Apps & Features.")


def write_manifest_draft(draft: ManifestDraft, output_root: Path) -> list[Path]:
    """Write a generated set under *output_root* and return its file paths."""
    written: list[Path] = []
    for relative, content in draft.files.items():
        path = output_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="\n")
        written.append(path)
    return written


__all__ = [
    "ManifestDraft",
    "build_manifest_draft",
    "load_catalog",
    "validate_manifest_files",
    "validate_templates",
    "write_manifest_draft",
]
