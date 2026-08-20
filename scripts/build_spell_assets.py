"""Build spell-check dictionary release assets from LibreOffice's dictionaries.

WHY THIS EXISTS
---------------
``quill/core/release_assets.py`` declares each downloadable Hunspell language as
a pinned, SHA-256-verified zip (``spell-<tag>.zip``) on the ``assets-v1``
release. The first two (es_ES, fr_FR) were assembled by hand from the
LibreOffice dictionaries repository at commit ``93d537d`` and the process was
not written down. This script is that process: for each requested language it

1. lists the language's directory in LibreOffice/dictionaries at the SAME
   pinned commit the existing assets used (byte-reproducible),
2. downloads ``<tag>.dic`` and ``<tag>.aff`` plus every license/readme file
   beside them (the GPL/LGPL/MPL terms require the notice to travel with the
   words),
3. packs them into ``spell-<tag>.zip``, and
4. prints a size table plus ready-to-paste ``ReleaseAsset`` entries with the
   real SHA-256 of each zip.

The zips are NOT added to ``release_assets.ASSETS`` by this script: an entry
whose zip is not yet uploaded to the release would make the language chooser
offer a download that 404s. Build, upload (``gh release upload assets-v1
dist/spell-assets/*.zip``), then paste the printed entries.

Usage::

    python scripts/build_spell_assets.py            # the standard tranche
    python scripts/build_spell_assets.py de_DE ru_RU  # specific languages
"""

from __future__ import annotations

import hashlib
import io
import json
import sys
import urllib.request
import zipfile
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_OUT_DIR = _REPO_ROOT / "dist" / "spell-assets"

#: The libreoffice/dictionaries commit the shipped es_ES/fr_FR assets were cut
#: from (see quill/core/release_assets.py "version" fields). Every language must
#: come from one commit or "libreoffice-dictionaries 93d537d" stops being true.
_PIN = "93d537d"

_API = "https://api.github.com/repos/LibreOffice/dictionaries/contents/{path}?ref=" + _PIN

#: language tag -> (dic/aff directory, dic/aff basename, license directory).
#: The basename is not always "<tag>" (German ships the frami variant;
#: Norwegian lives under "no"), and Swedish nests its .dic/.aff a level below
#: the directory holding its LICENSE/README files.
_SOURCES: dict[str, tuple[str, str, str]] = {
    "cs_CZ": ("cs_CZ", "cs_CZ", "cs_CZ"),
    "da_DK": ("da_DK", "da_DK", "da_DK"),
    "de_DE": ("de", "de_DE_frami", "de"),
    "it_IT": ("it_IT", "it_IT", "it_IT"),
    "nb_NO": ("no", "nb_NO", "no"),
    "nl_NL": ("nl_NL", "nl_NL", "nl_NL"),
    "pl_PL": ("pl_PL", "pl_PL", "pl_PL"),
    "pt_BR": ("pt_BR", "pt_BR", "pt_BR"),
    "pt_PT": ("pt_PT", "pt_PT", "pt_PT"),
    "ro_RO": ("ro", "ro_RO", "ro"),
    "ru_RU": ("ru_RU", "ru_RU", "ru_RU"),
    "sv_SE": ("sv_SE/dictionaries", "sv_SE", "sv_SE"),
}

#: Upstream license notes for the printed ReleaseAsset entries, mirroring the
#: existing es_ES/fr_FR phrasing. Checked against each directory's README.
_LICENSES: dict[str, str] = {
    "cs_CZ": "GPL-2.0 (LibreOffice cs_CZ)",
    "da_DK": "GPL-2.0/LGPL-2.1/MPL-1.1 (LibreOffice da_DK / Stavekontrolden)",
    "de_DE": "GPL-2.0/GPL-3.0 (LibreOffice de / frami)",
    "it_IT": "GPL-3.0 (LibreOffice it_IT / linguistico)",
    "nb_NO": "GPL-2.0 (LibreOffice no)",
    "nl_NL": "BSD-3-Clause/CC-BY-3.0 (LibreOffice nl_NL / OpenTaal)",
    "pl_PL": "GPL-3.0/LGPL-3.0/MPL-2.0 (LibreOffice pl_PL / sjp.pl)",
    "pt_BR": "LGPL-3.0/MPL-2.0 (LibreOffice pt_BR / VERO)",
    "pt_PT": "GPL-2.0/LGPL-2.1/MPL-1.1 (LibreOffice pt_PT / Natura Minho)",
    "ro_RO": "GPL-2.0/LGPL-2.1/MPL-1.1 (LibreOffice ro / rospell)",
    "ru_RU": "BSD-like (LibreOffice ru_RU / AOT.ru)",
    "sv_SE": "LGPL-3.0 (LibreOffice sv_SE / DSSO)",
}

_LICENSE_HINTS = ("readme", "license", "licence", "copying", "gpl", "lgpl", "mpl")


def _fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "quill-build-spell-assets"})
    with urllib.request.urlopen(request, timeout=120) as response:  # noqa: S310 - https only
        return response.read()


def _listing(directory: str) -> list[dict]:
    return json.loads(_fetch(_API.format(path=directory)))


def _build_language(tag: str) -> tuple[Path, str, int] | None:
    directory, basename, license_dir = _SOURCES[tag]
    entries = {item["name"]: item for item in _listing(directory) if item["type"] == "file"}
    wanted: dict[str, tuple[dict, str]] = {}
    for suffix in (".dic", ".aff"):
        name = f"{basename}{suffix}"
        if name not in entries:
            print(f"  {tag}: {name} not found in {directory}/ at {_PIN} -- skipped")
            return None
        # The zip member is <tag>.dic/.aff regardless of the upstream basename:
        # enchant resolves languages by file name, so de_DE_frami.dic must land
        # as de_DE.dic.
        wanted[name] = (entries[name], f"{tag}{suffix}")
    license_entries = (
        entries
        if license_dir == directory
        else {item["name"]: item for item in _listing(license_dir) if item["type"] == "file"}
    )
    for name, item in license_entries.items():
        lowered = name.lower()
        if any(hint in lowered for hint in _LICENSE_HINTS) and not lowered.endswith((
            ".dic",
            ".aff",
        )):
            wanted.setdefault(name, (item, name))

    _OUT_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = _OUT_DIR / f"spell-{tag}.zip"
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as pack:
        for _upstream_name, (item, member) in sorted(wanted.items()):
            pack.writestr(member, _fetch(item["download_url"]))
    zip_path.write_bytes(buffer.getvalue())
    digest = hashlib.sha256(buffer.getvalue()).hexdigest()
    return zip_path, digest, len(buffer.getvalue())


def _entry(tag: str, digest: str) -> str:
    license_note = _LICENSES.get(tag, "see README inside zip")
    return (
        f'    "spell-{tag}": ReleaseAsset(\n'
        f'        component="spell-{tag}",\n'
        f'        tag="assets-v1",\n'
        f'        filename="spell-{tag}.zip",\n'
        f'        sha256="{digest}",\n'
        f'        expect_member="{tag}.dic",\n'
        f'        license="{license_note}",\n'
        f'        version="libreoffice-dictionaries {_PIN}",\n'
        f"    ),"
    )


def main() -> int:
    tags = sys.argv[1:] or sorted(_SOURCES)
    unknown = [tag for tag in tags if tag not in _SOURCES]
    if unknown:
        print(f"Unknown language tag(s): {', '.join(unknown)}")
        print(f"Known: {', '.join(sorted(_SOURCES))}")
        return 2

    built: list[tuple[str, str, int]] = []
    print(f"Building {len(tags)} spell asset(s) from LibreOffice/dictionaries @ {_PIN}\n")
    for tag in tags:
        result = _build_language(tag)
        if result is None:
            continue
        zip_path, digest, size = result
        built.append((tag, digest, size))
        print(f"  {tag}: {zip_path.name}  {size / 1024 / 1024:.2f} MB  sha256 {digest[:16]}...")

    if not built:
        print("Nothing built.")
        return 1

    print("\nSize table (zip, as distributed):")
    for tag, _digest, size in built:
        print(f"  {tag}: {size / 1024 / 1024:.2f} MB")
    print(f"  total: {sum(size for _t, _d, size in built) / 1024 / 1024:.2f} MB")

    print("\nUpload, then paste into quill/core/release_assets.py ASSETS:\n")
    print(f"  gh release upload assets-v1 {_OUT_DIR}\\spell-*.zip\n")
    for tag, digest, _size in built:
        print(_entry(tag, digest))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
