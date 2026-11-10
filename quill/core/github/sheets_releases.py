"""Sheets for releases, release assets and packages (GitHub PRD Appendix C, Phase 8).

A release's tag, target, title, notes, draft, pre-release and latest flags;
an asset's file name and label; a package's facts (GitHub changes a package's
visibility and access on its settings page only, and the sheet says so).

wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from quill.core.github.permissions import WriteTier
from quill.core.github.sheet_engine import Ident, Read, SheetDef
from quill.core.github.sheet_fields import dig, ed, lst, page, patch, ro, when
from quill.core.workbench.properties import FieldKind, SheetSpec, Value

__all__ = ["PACKAGE", "RELEASE", "RELEASE_ASSET"]

_O, _V, _A, _D = (
    WriteTier.ORGANIZING,
    WriteTier.VISIBLE,
    WriteTier.ACCESS,
    WriteTier.DESTRUCTIVE,
)
_K = FieldKind
_ACT = "/repos/{repo}/actions"


# -- releases and packages ----------------------------------------------------------


def _release(data: Mapping[str, Any]) -> dict[str, Value]:
    return {
        "id": str(data.get("id") or ""),
        "tag": str(data.get("tag_name") or ""),
        "target": str(data.get("target_commitish") or ""),
        "name": str(data.get("name") or ""),
        "notes": str(data.get("body") or ""),
        "draft": bool(data.get("draft")),
        "prerelease": bool(data.get("prerelease")),
        "author": str(dig(data, "author", "login") or ""),
        "published": when(data.get("published_at")),
        "assets": tuple(
            f"{a.get('name', '')}, {int(a.get('size') or 0) // 1024} KB, "
            f"{a.get('download_count', 0)} downloads"
            for a in lst(data, "assets")
            if isinstance(a, Mapping)
        ),
        "discussion": str(data.get("discussion_url") or ""),
        "url": str(data.get("html_url") or ""),
    }


def _latest(data: Mapping[str, Any], ident: Ident) -> dict[str, Value]:
    return {"latest": str(data.get("tag_name") or "") == ident.get("tag", "")}


def _make_latest(value: Value, _c: Mapping[str, object], _i: Ident) -> dict[str, object]:
    return {"make_latest": "true" if value else "false"}


_REL = "/repos/{repo}/releases/{id}"

RELEASE = SheetDef(
    "release",
    SheetSpec(
        "release",
        "Release",
        (
            page(
                "general",
                "General",
                ed("name", "Title"),
                ed("tag", "Tag"),
                ed("target", "Target", help="The branch or commit the tag is made on."),
                ed("draft", "Draft", _K.CHECK, "Publishing a draft is clearing this."),
                ed("prerelease", "Pre-release", _K.CHECK),
                ed("latest", "Latest release", _K.CHECK),
                ro("author", "Author"),
                ro("published", "Published", _K.DATE),
                ro("url", "Address", _K.LINK),
            ),
            page("notes", "Notes", ed("notes", "Release notes", _K.MULTILINE, "Markdown.")),
            page(
                "assets",
                "Assets",
                ro(
                    "assets",
                    "Assets",
                    _K.TABLE,
                    "Each file; its own sheet renames it or changes its label.",
                ),
            ),
            page("discussion", "Discussion", ro("discussion", "Discussion", _K.LINK)),
        ),
    ),
    (
        Read("/repos/{repo}/releases/tags/{tag}", _release),
        Read(
            "/repos/{repo}/releases/latest", pick=_latest, optional=True, fallback={"latest": False}
        ),
    ),
    {
        "name": patch(_REL, "repo:write", _V),
        "tag": patch(_REL, "repo:write", _V, "tag_name"),
        "target": patch(_REL, "repo:write", _V, "target_commitish"),
        "draft": patch(_REL, "repo:write", _V),
        "prerelease": patch(_REL, "repo:write", _V),
        "latest": patch(_REL, "repo:write", _V, encode=_make_latest),
        "notes": patch(_REL, "repo:write", _V, "body"),
    },
    title=lambda ident: f"Release {ident['tag']}",
    url=lambda ident: f"https://github.com/{ident['repo']}/releases/tag/{ident['tag']}",
    adopt=("id",),
    renames=("tag", "tag"),
)


def _asset(data: Mapping[str, Any], ident: Ident) -> dict[str, Value]:
    for asset in lst(data, "assets"):
        if isinstance(asset, Mapping) and asset.get("name") == ident.get("name"):
            return {
                "asset_id": str(asset.get("id") or ""),
                "name": str(asset.get("name") or ""),
                "label": str(asset.get("label") or ""),
                "size": f"{int(asset.get('size') or 0) // 1024} KB",
                "downloads": int(asset.get("download_count") or 0),
                "content_type": str(asset.get("content_type") or ""),
                "updated": when(asset.get("updated_at")),
                "url": str(asset.get("browser_download_url") or ""),
            }
    return {}


_ASSET = "/repos/{repo}/releases/assets/{asset_id}"

RELEASE_ASSET = SheetDef(
    "release_asset",
    SheetSpec(
        "release_asset",
        "Release Asset",
        (
            page(
                "general",
                "General",
                ed("name", "File name"),
                ed("label", "Label"),
                ro("size", "Size"),
                ro("downloads", "Downloads", _K.NUMBER),
                ro("content_type", "Content type"),
                ro("updated", "Updated", _K.DATE),
                ro("url", "Download address", _K.LINK),
            ),
        ),
    ),
    (Read("/repos/{repo}/releases/tags/{tag}", pick=_asset),),
    {"name": patch(_ASSET, "repo:write", _V), "label": patch(_ASSET, "repo:write", _V)},
    title=lambda ident: f"Asset {ident['name']}",
    adopt=("asset_id",),
    renames=("name", "name"),
)


def _package(data: Mapping[str, Any]) -> dict[str, Value]:
    return {
        "name": str(data.get("name") or ""),
        "type": str(data.get("package_type") or ""),
        "visibility": str(data.get("visibility") or ""),
        "repository": str(dig(data, "repository", "full_name") or ""),
        "versions": int(data.get("version_count") or 0),
        "updated": when(data.get("updated_at")),
        "url": str(data.get("html_url") or ""),
    }


PACKAGE = SheetDef(
    "package",
    SheetSpec(
        "package",
        "Package",
        (
            page(
                "general",
                "General",
                ro("name", "Name"),
                ro("type", "Type"),
                ro(
                    "visibility",
                    "Visibility",
                    help="GitHub changes a package's visibility on its "
                    "settings page only; Open on GitHub goes there.",
                ),
                ro("updated", "Updated", _K.DATE),
                ro("url", "Address", _K.LINK),
            ),
            page("versions", "Versions", ro("versions", "Versions", _K.NUMBER)),
            page(
                "access",
                "Access",
                ro(
                    "access_note",
                    "Access",
                    help="Package access is set on GitHub's package settings page; it has no API.",
                ),
            ),
            page("repository", "Repository", ro("repository", "Linked repository")),
        ),
    ),
    (Read("/{owner_path}/packages/{package_type}/{name}", _package),),
    title=lambda ident: f"Package {ident['name']}",
)
