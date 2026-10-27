"""Third-party notices for the QUILL family, rendered from one catalogue.

Every bundled or redistributed third-party component of every product is one
entry in ``quill/data/third_party/components.json``; the full licence texts it
cites live beside it in ``licenses/``. This module reads that catalogue and
renders it three ways:

* :func:`render_markdown` -- the family document,
  ``docs/legal/THIRD_PARTY_NOTICES.md``;
* :func:`render_text` -- the same in plain text, either for the whole family
  (``docs/legal/THIRD_PARTY_NOTICES.txt``) or for one product
  (``standalone/<app>/THIRD-PARTY-NOTICES.txt``, which its installer and
  portable zip ship beside the program);
* :func:`render_license_txt` -- the product's own licence as ``LICENSE.txt``.

The layout is built for listening. One heading per component, grouped by kind,
so a screen reader's heading list is the table of contents; every entry says
the same things in the same order; and each licence text appears once, in the
appendix, with the components that use it named above it rather than repeated
forty times.

Nothing here reads the installed environment, so what it renders depends only
on files in the repository. ``quill/tools/build_third_party_notices.py`` writes
the outputs and checks them for drift.

wx-free and strict-typed.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

__all__ = [
    "ALL",
    "Catalogue",
    "Component",
    "load_catalogue",
    "render_license_txt",
    "render_markdown",
    "render_text",
]

#: The products value meaning "every product in the family".
ALL = "all"

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "quill" / "data" / "third_party"
CATALOGUE_PATH = DATA_DIR / "components.json"
LICENSE_DIR = DATA_DIR / "licenses"

_DELIVERY = {
    "bundled": "Bundled: it is inside the installer or the portable zip.",
    "shared-runtime": (
        "Bundled in the QuillVille Runtime used by installed app editions. "
        "A standalone portable includes it only when that app's declared "
        "dependencies require it."
    ),
    "on-request": (
        "Downloaded only when you ask for it, from QUILL's own pinned release, "
        "so QUILL still redistributes it."
    ),
    "build-only": "Used only to build the products. Not shipped to you.",
}

_SUPPORT = "support@community-access.org"
_SOURCE_URL = "https://github.com/Community-Access/quill"


@dataclass(frozen=True)
class Component:
    """One catalogue entry."""

    id: str
    name: str
    group: str
    version: str
    licenses: tuple[str, ...]
    license_label: str
    copyright: str
    homepage: str
    what: str
    products: tuple[str, ...]
    delivery: str
    obligations: str = ""
    review: str = ""
    pypi: str = ""
    source_url: str = ""
    source_sha256: str = ""

    def ships_in(self, product: str | None) -> bool:
        """Whether *product* carries this component (None means the family)."""
        if product is None:
            return True
        if self.delivery == "build-only":
            return False
        return ALL in self.products or product in self.products


@dataclass(frozen=True)
class Catalogue:
    """The parsed catalogue: products, groups, licences and components."""

    products: dict[str, dict[str, Any]]
    groups: list[dict[str, str]]
    licenses: dict[str, dict[str, Any]]
    components: list[Component]

    def product_name(self, key: str) -> str:
        return str(self.products[key]["name"])

    def for_product(self, product: str | None) -> list[Component]:
        return [item for item in self.components if item.ships_in(product)]

    def license_text(self, key: str) -> str | None:
        """The full text of licence *key*, or None when it is only referenced."""
        ref = self.licenses[key].get("text")
        if not ref:
            return None
        ref = str(ref)
        if ref.startswith("repo:"):
            path = REPO_ROOT / ref.removeprefix("repo:")
        else:
            path = LICENSE_DIR / ref
        return path.read_text(encoding="utf-8").replace("\r\n", "\n").strip("\n")


def load_catalogue(path: Path = CATALOGUE_PATH) -> Catalogue:
    """Parse the catalogue at *path*, failing loudly on an unknown key."""
    data = json.loads(path.read_text(encoding="utf-8"))
    licenses: dict[str, dict[str, Any]] = data["licenses"]
    products: dict[str, dict[str, Any]] = data["products"]
    groups: list[dict[str, str]] = data["groups"]
    group_ids = {group["id"] for group in groups}
    components: list[Component] = []
    for raw in data["components"]:
        item = Component(
            id=raw["id"],
            name=raw["name"],
            group=raw["group"],
            version=raw["version"],
            licenses=tuple(raw["licenses"]),
            license_label=raw["license_label"],
            copyright=raw["copyright"],
            homepage=raw.get("homepage", ""),
            what=raw["what"],
            products=tuple(raw["products"]),
            delivery=raw["delivery"],
            obligations=raw.get("obligations", ""),
            review=raw.get("review", ""),
            pypi=raw.get("pypi", ""),
            source_url=raw.get("source_url", ""),
            source_sha256=raw.get("source_sha256", ""),
        )
        unknown = [key for key in item.licenses if key not in licenses]
        if unknown:
            raise ValueError(f"{item.id}: unknown licence {unknown}")
        bad = [key for key in item.products if key != ALL and key not in products]
        if bad:
            raise ValueError(f"{item.id}: unknown product {bad}")
        if item.group not in group_ids:
            raise ValueError(f"{item.id}: unknown group {item.group}")
        if item.delivery not in _DELIVERY:
            raise ValueError(f"{item.id}: unknown delivery {item.delivery}")
        components.append(item)
    return Catalogue(products, groups, licenses, components)


# -- shared wording ------------------------------------------------------------


def _included_in(cat: Catalogue, item: Component) -> str:
    if item.delivery == "shared-runtime":
        return (
            "The QuillVille Runtime and installed app editions that include it. "
            "Standalone portable editions are scoped by their own dependency "
            "inventories."
        )
    if ALL in item.products:
        return "Every product in the family."
    names = [cat.product_name(key) for key in cat.products if key in item.products]
    return ", ".join(names) + "."


def _obligations(cat: Catalogue, item: Component) -> str:
    if item.obligations:
        return item.obligations
    parts = [str(cat.licenses[key]["obligations"]) for key in item.licenses]
    unique: list[str] = []
    for part in parts:
        if part not in unique:
            unique.append(part)
    return " ".join(unique)


def _fields(cat: Catalogue, item: Component, *, family: bool) -> list[tuple[str, str]]:
    rows = [("What it is", item.what)]
    if family:
        rows.append(("Included in", _included_in(cat, item)))
    rows += [
        ("Version", item.version),
        ("Licence", item.license_label),
        ("Copyright", item.copyright),
    ]
    if item.homepage:
        rows.append(("Upstream", item.homepage))
    if item.source_url:
        source = item.source_url
        if item.source_sha256:
            source += f" (SHA-256: {item.source_sha256})"
        rows.append(("Source distribution", source))
    rows += [
        ("How it reaches you", _DELIVERY[item.delivery]),
        ("What the licence asks of us", _obligations(cat, item)),
    ]
    # Review notes are for the people maintaining the family, so they appear in
    # the family document and not in the file an installer ships to a listener.
    if item.review and family:
        rows.append(("Needs review", item.review))
    return rows


def _license_counts(items: Iterable[Component]) -> list[tuple[str, int]]:
    counts: dict[str, int] = {}
    for item in items:
        for key in item.licenses:
            counts[key] = counts.get(key, 0) + 1
    return sorted(counts.items(), key=lambda pair: (-pair[1], pair[0]))


def _used_licenses(items: Iterable[Component]) -> list[str]:
    return sorted({key for item in items for key in item.licenses}, key=str.lower)


def _intro(cat: Catalogue, product: str | None) -> list[str]:
    who = "the QUILL family" if product is None else cat.product_name(product)
    paras = [
        f"This document lists the third-party software, data, models and sounds "
        f"included in {who}, with each one's licence, copyright holder and what its "
        "licence asks of us. QUILL and every app in the family are free and never sold.",
        "The family's own code is released under the MIT License; see LICENSE.txt "
        "beside the program, or the LICENSE file in the source repository.",
        "Each component has its own heading, grouped by kind. The full licence texts "
        "follow in the appendix, each once, with the components that use it named "
        "above it.",
    ]
    if product is not None:
        paras.append(
            "Installed copies run on the shared QuillVille Runtime, so the libraries in "
            "it are listed here even when this app does not call them. Components that "
            "are only downloaded when you ask for them are listed too, because QUILL "
            "redistributes them from its own release."
        )
    paras.append(
        "This file is generated from quill/data/third_party/components.json by "
        "quill/tools/build_third_party_notices.py. Do not edit it by hand."
    )
    return paras


def _source_offer() -> list[str]:
    return [
        "Some components are under the GNU GPL, LGPL or AGPL, or the Mozilla Public "
        "License. Their source requirements depend on the licence and the work being "
        "conveyed. Each entry identifies the version and, where recorded, a "
        "version-specific source location. QUILL keeps release-specific source and "
        "build instructions according to the applicable terms; to request source "
        f"materials or a written offer, write to {_SUPPORT}.",
        f"QUILL's own source code is public at {_SOURCE_URL}. For PyMuPDF, the entry "
        "above names the exact source archive and its SHA-256 checksum. The source "
        "scope for a QUILL work combined with an AGPL component is subject to legal "
        "review; this notice does not make a blanket relicensing claim.",
    ]


# -- Markdown ------------------------------------------------------------------


def render_markdown(cat: Catalogue) -> str:
    """The family document, docs/legal/THIRD_PARTY_NOTICES.md."""
    items = cat.for_product(None)
    out = ["# Third-Party Notices", ""]
    for para in _intro(cat, None):
        out += [para, ""]
    out += ["## Products covered", ""]
    for key in cat.products:
        out.append(f"- {cat.product_name(key)}")
    out += ["", "## Summary by licence", ""]
    for key, count in _license_counts(items):
        noun = "component" if count == 1 else "components"
        out.append(f"- {cat.licenses[key]['name']}: {count} {noun}")
    out += ["", "## Items that need review", ""]
    out += [
        "These entries carry a licence that could not be confirmed, or an obligation "
        "the owner should decide on. Each one says why under its own heading.",
        "",
    ]
    for item in items:
        if item.review:
            out.append(f"- {item.name}")
    out.append("")
    for group in cat.groups:
        members = [item for item in items if item.group == group["id"]]
        if not members:
            continue
        out += [f"## {group['title']}", "", group["intro"], ""]
        for item in members:
            out += [f"### {item.name}", ""]
            for label, value in _fields(cat, item, family=True):
                out.append(f"- **{label}:** {value}")
            out.append("")
    out += ["## Source code offer", ""]
    for para in _source_offer():
        out += [para, ""]
    out += ["## Appendix: licence texts", ""]
    for key in _used_licenses(items):
        out += _markdown_licence(cat, key, items)
    return "\n".join(out).rstrip() + "\n"


def _markdown_licence(cat: Catalogue, key: str, items: list[Component]) -> list[str]:
    meta = cat.licenses[key]
    users = [item.name for item in items if key in item.licenses]
    out = [f"### {meta['name']}", ""]
    out += [f"Used by: {', '.join(users)}.", ""]
    out += [f"What it asks of us: {meta['obligations']}", ""]
    text = cat.license_text(key)
    if text is None:
        url = meta.get("url")
        where = f" It is published at {url}." if url else ""
        out += [f"The full text is not reproduced here.{where}", ""]
    else:
        out += ["````text", text, "````", ""]
    return out


# -- plain text ----------------------------------------------------------------


def _heading(text: str, rule: str) -> list[str]:
    return [text, rule * len(text), ""]


def render_text(cat: Catalogue, product: str | None = None) -> str:
    """Plain-text notices for the family (None) or for one *product*."""
    items = cat.for_product(product)
    title = (
        "Third-Party Notices"
        if product is None
        else f"{cat.product_name(product)}: Third-Party Notices"
    )
    out = _heading(title, "=")
    for para in _intro(cat, product):
        out += [para, ""]
    out += _heading("Summary by licence", "-")
    for key, count in _license_counts(items):
        noun = "component" if count == 1 else "components"
        out.append(f"  {cat.licenses[key]['name']}: {count} {noun}")
    out.append("")
    if product is None:
        out += _heading("Items that need review", "-")
        out += [f"  {item.name}" for item in items if item.review]
        out.append("")
    for group in cat.groups:
        members = [item for item in items if item.group == group["id"]]
        if not members:
            continue
        out += _heading(group["title"].upper(), "=")
        out += [group["intro"], ""]
        for item in members:
            out += _heading(item.name, "-")
            for label, value in _fields(cat, item, family=product is None):
                out.append(f"{label}: {value}")
            out.append("")
    out += _heading("SOURCE CODE OFFER", "=")
    for para in _source_offer():
        out += [para, ""]
    out += _heading("APPENDIX: LICENCE TEXTS", "=")
    for key in _used_licenses(items):
        meta = cat.licenses[key]
        users = [item.name for item in items if key in item.licenses]
        out += _heading(str(meta["name"]), "-")
        out += [f"Used by: {', '.join(users)}.", ""]
        out += [f"What it asks of us: {meta['obligations']}", ""]
        text = cat.license_text(key)
        if text is None:
            url = meta.get("url")
            where = f" It is published at {url}." if url else ""
            out += [f"The full text is not reproduced here.{where}", ""]
        else:
            out += [text, ""]
    return "\n".join(out).rstrip() + "\n"


def render_license_txt(cat: Catalogue, product: str) -> str:
    """*product*'s own licence: the family's MIT License, named for the app."""
    body = (REPO_ROOT / "LICENSE").read_text(encoding="utf-8").replace("\r\n", "\n")
    name = cat.product_name(product)
    header = (
        f"{name} is part of the QUILL family and is released under the MIT License "
        "below.\nThe third-party components it includes, and their licences, are "
        "listed in THIRD-PARTY-NOTICES.txt beside this file.\n\n"
    )
    return header + body.strip("\n") + "\n"
