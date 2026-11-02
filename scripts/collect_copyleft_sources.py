"""List the copyleft components a release ships, and where their source is.

Every GPL, AGPL or LGPL component in a QuillVille release owes its exact
Corresponding Source (GPLv3/AGPLv3 section 6, LGPL's source terms). The
licensing review of 2026-11-01 settled the mechanism: one source bundle per
release, published beside the binaries. This script is the first half of
that bundle. Given the runtime build folder it:

* lists every GPL/AGPL/LGPL component from the notice catalogue
  (``quill/data/third_party/components.json``) that ships in the product,
  with its exact version -- read from the build's own ``*.dist-info`` folders
  and bundled licence files where it can, from the catalogue otherwise, and
  says which;
* names the matching source archive for each one: the PyPI sdist for a
  Python package, the upstream tag archive for a native library (libmpv,
  x265, libheif, libde265, the MSYS2 GCC runtime, FFmpeg, eSpeak NG and the
  rest), and ``git archive`` of QUILL itself at the release commit;
* writes ``copyleft-sources.json`` (the manifest) and ``copyleft-sources.txt``
  (the same list as plain text, with the commands to fetch each archive).

It never touches the network unless ``--download`` is given; then it fetches
every archive it can into ``<out>/sources``. Build-only tools (PyInstaller,
the Pandoc that renders the docs) are not distributed and are left out.

Usage::

    python scripts/collect_copyleft_sources.py --product radio \\
        --build-dir standalone/runtime/dist/QuillVilleRuntime --out dist/sources
    python scripts/collect_copyleft_sources.py --product quill --out dist/sources --download
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from quill.core.third_party_notices import Catalogue, Component, load_catalogue  # noqa: E402

#: The licences whose terms require us to offer source.
COPYLEFT = frozenset({"GPL-2.0", "GPL-3.0", "AGPL-3.0", "LGPL-2.1", "LGPL-3.0"})

#: Not distributed: used on the build machine only.
_NOT_SHIPPED = frozenset({"build-only"})

MANIFEST_JSON = "copyleft-sources.json"
MANIFEST_TXT = "copyleft-sources.txt"


@dataclass
class Source:
    """One archive to fetch: a PyPI sdist (``pypi``) or a URL (``url``)."""

    label: str
    version: str
    kind: str  # "pypi" | "url" | "git-archive" | "note"
    url: str = ""
    command: str = ""
    sha256: str = ""
    version_from: str = "catalogue"


@dataclass
class Entry:
    id: str
    name: str
    licences: list[str]
    delivery: str
    version: str
    version_from: str
    sources: list[Source] = field(default_factory=list)


# -- what the build folder can tell us -------------------------------------------


def build_versions(build_dir: Path | None) -> dict[str, str]:
    """Distribution name (normalised) -> version, from ``*.dist-info`` folders."""
    found: dict[str, str] = {}
    if build_dir is None or not build_dir.is_dir():
        return found
    for info in build_dir.rglob("*.dist-info"):
        match = re.match(r"^(.+?)-([^-]+)\.dist-info$", info.name)
        if match:
            found[_norm(match.group(1))] = match.group(2)
    return found


def bundled_heif_sources(build_dir: Path | None) -> dict[str, str]:
    """libheif/libde265/x265 -> their "Source code:" URL, from pillow-heif's own list."""
    sources: dict[str, str] = {}
    if build_dir is None or not build_dir.is_dir():
        return sources
    for path in build_dir.rglob("LICENSES_bundled.txt"):
        name = ""
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("Name:"):
                name = line.split(":", 1)[1].strip()
            elif "Source code:" in line and name:
                sources[name] = line.split("Source code:", 1)[1].strip()
        if sources:
            break
    return sources


def gcc_versions(build_dir: Path | None) -> list[str]:
    """Every GCC version stamped in the bundled libgcc/libstdc++ DLLs (sorted)."""
    versions: set[str] = set()
    if build_dir is None or not build_dir.is_dir():
        return []
    for pattern in ("libstdc++*.dll", "libgcc_s_seh*.dll"):
        for dll in build_dir.rglob(pattern):
            data = dll.read_bytes()
            for match in re.finditer(rb"GCC: \([^)]*\) (\d+\.\d+\.\d+)", data):
                versions.add(match.group(1).decode("ascii"))
    return sorted(versions)


def _norm(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


# -- where each component's source lives -------------------------------------------


def _pypi(name: str, version: str, version_from: str, *, url: str = "", sha: str = "") -> Source:
    return Source(
        label=f"{name} {version} (PyPI sdist)",
        version=version,
        kind="pypi",
        url=url or f"https://pypi.org/project/{name}/{version}/#files",
        command=f"python -m pip download --no-deps --no-binary :all: {name}=={version}",
        sha256=sha,
        version_from=version_from,
    )


def _url(label: str, version: str, url: str, version_from: str = "catalogue") -> Source:
    return Source(label=label, version=version, kind="url", url=url, version_from=version_from)


def _note(label: str, text: str) -> Source:
    return Source(label=label, version="", kind="note", command=text)


def native_sources(item: Component, build_dir: Path | None) -> list[Source]:
    """Upstream source archives for the native (non-PyPI) copyleft components."""
    heif = bundled_heif_sources(build_dir)
    if item.id == "pillow-heif":
        out = []
        for name, default in (
            ("libheif", "https://github.com/strukturag/libheif/tree/v1.23.6"),
            ("libde265", "https://github.com/strukturag/libde265/tree/v1.1.3"),
            ("x265", "https://github.com/Multicorewareinc/x265/tree/4.3"),
        ):
            url = heif.get(name, default)
            tag = url.rstrip("/").rsplit("/", 1)[-1]
            repo = url.split("/tree/", 1)[0]
            out.append(
                _url(
                    f"{name} {tag} (bundled in pillow-heif)",
                    tag,
                    f"{repo}/archive/refs/tags/{tag}.tar.gz",
                    "build" if name in heif else "catalogue",
                )
            )
        return out
    if item.id == "mingw-runtime":
        found = gcc_versions(build_dir)
        versions = found or ["16.2.0", "13.1.0", "12.2.0"]
        return [
            _url(
                f"MSYS2 mingw-w64-gcc {v} source package (libgcc, libstdc++)",
                v,
                "https://repo.msys2.org/mingw/sources/",
                "build" if found else "catalogue",
            )
            for v in versions
        ]
    table: dict[str, list[Source]] = {
        "libmpv": [
            _url(
                "mpv at commit a58dd8a (the shinchiro mpv-winbuild-cmake build of 2025-12-28)",
                "a58dd8a",
                "https://github.com/mpv-player/mpv/archive/a58dd8a.tar.gz",
            ),
            _note(
                "mpv-winbuild-cmake and its pinned dependencies",
                "Add the shinchiro mpv-winbuild-cmake commit used for this libmpv and the "
                "source tarballs that build fetched (FFmpeg, libass and the rest).",
            ),
        ],
        "ffmpeg": [
            _url("FFmpeg 8.1.2", "8.1.2", "https://ffmpeg.org/releases/ffmpeg-8.1.2.tar.xz")
        ],
        "espeak-ng": [
            _url(
                "eSpeak NG 1.52.0",
                "1.52.0",
                "https://github.com/espeak-ng/espeak-ng/archive/refs/tags/1.52.0.tar.gz",
            )
        ],
        "kokoro": [
            _pypi("phonemizer", "3.4.0", "catalogue"),
            _pypi("espeakng-loader", "0.2.4", "catalogue"),
        ],
        "pandoc": [
            _url(
                "Pandoc 3.10", "3.10", "https://github.com/jgm/pandoc/archive/refs/tags/3.10.tar.gz"
            )
        ],
        "liblouis": [
            _url(
                "liblouis 3.38.0",
                "3.38.0",
                "https://github.com/liblouis/liblouis/releases/download/v3.38.0/liblouis-3.38.0.tar.gz",
            )
        ],
        "git-gh": [
            _url(
                "Git for Windows 2.55.0.windows.2 (MinGit)",
                "2.55.0.windows.2",
                "https://github.com/git-for-windows/git/archive/refs/tags/v2.55.0.windows.2.tar.gz",
            )
        ],
        "hunspell-dictionaries": [
            _url(
                "LibreOffice dictionaries at commit 93d537d",
                "93d537d",
                "https://github.com/LibreOffice/dictionaries/archive/93d537d.tar.gz",
            )
        ],
        "th-en-us": [
            _note("English thesaurus data", "Carried in the QUILL source archive (quill/data).")
        ],
    }
    return table.get(item.id, [_note(item.name, "No source archive is known; add one here.")])


def python_sources(item: Component, versions: dict[str, str]) -> list[Source]:
    built = versions.get(_norm(item.pypi))
    version = built or item.version
    origin = "build" if built else "catalogue"
    if item.id == "pywin32":  # no sdist on PyPI; the tag archive is the source
        return [
            _url(
                f"pywin32 build {version}",
                version,
                f"https://github.com/mhammond/pywin32/archive/refs/tags/b{version}.tar.gz",
                origin,
            )
        ]
    url = item.source_url if item.source_url and version in item.source_url else ""
    sha = item.source_sha256 if url else ""
    out = [_pypi(item.pypi, version, origin, url=url, sha=sha)]
    if item.id == "pyenchant":
        out.append(
            _note(
                "PyEnchant payload libraries",
                "Enchant, GLib, libiconv, gettext (libintl), Hunspell and PCRE2 from the MSYS2 "
                "source packages (https://repo.msys2.org/mingw/sources/) matching the DLLs in "
                "enchant/data/mingw64/bin.",
            )
        )
    return out


def quill_source(commit: str) -> Source:
    return Source(
        label=f"QUILL at {commit}, with uv.lock and vendor/wheels",
        version=commit,
        kind="git-archive",
        url="https://github.com/Community-Access/quill",
        command=f"git archive --format=zip -o quill-{commit}-source.zip {commit}",
    )


def release_commit() -> str:
    try:
        done = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return "<release commit>"
    return done.stdout.strip() or "<release commit>"


# -- the manifest ---------------------------------------------------------------


def collect(
    catalogue: Catalogue, product: str | None, build_dir: Path | None = None
) -> list[Entry]:
    """Every copyleft component that ships in *product* (None: the whole family)."""
    versions = build_versions(build_dir)
    entries: list[Entry] = []
    for item in catalogue.for_product(product):
        copyleft = [key for key in item.licenses if key in COPYLEFT]
        if not copyleft or item.delivery in _NOT_SHIPPED:
            continue
        sources = python_sources(item, versions) if item.pypi else native_sources(item, build_dir)
        if item.id == "pillow-heif":  # the wheel's GPL/LGPL libraries have their own sources
            sources += native_sources(item, build_dir)
        first = next((s for s in sources if s.kind != "note"), None)
        built = bool(item.pypi and versions.get(_norm(item.pypi)))
        entries.append(
            Entry(
                id=item.id,
                name=item.name,
                licences=list(item.licenses),
                delivery=item.delivery,
                version=first.version if (first and built) else item.version,
                version_from="build" if built else "catalogue",
                sources=sources,
            )
        )
    return entries


def manifest(
    entries: list[Entry], *, product: str | None, commit: str, build_dir: Path | None
) -> dict[str, object]:
    return {
        "product": product or "all",
        "quill_commit": commit,
        "build_dir": str(build_dir) if build_dir else "",
        "quill_source": asdict(quill_source(commit)),
        "components": [asdict(entry) for entry in entries],
    }


def render_text(data: dict[str, object]) -> str:
    lines = [
        f"Copyleft components and their source, product: {data['product']}",
        f"QUILL commit: {data['quill_commit']}",
        "",
        "Versions marked (build) were read from the build folder; (catalogue) from",
        "quill/data/third_party/components.json. Check every (catalogue) one against",
        "what shipped before publishing the source bundle.",
        "",
        "QUILL itself:",
    ]
    quill = data["quill_source"]
    assert isinstance(quill, dict)
    lines.append(f"- {quill['label']}: {quill['command']}")
    components = data["components"]
    assert isinstance(components, list)
    for entry in components:
        lines.append("")
        lines.append(
            f"{entry['name']} {entry['version']} ({entry['version_from']}), "
            f"licences {', '.join(entry['licences'])}, {entry['delivery']}:"
        )
        for source in entry["sources"]:
            if source["kind"] == "note":
                lines.append(f"- {source['label']}: {source['command']}")
                continue
            line = f"- {source['label']}: {source['url']}"
            if source["command"]:
                line += f"  ({source['command']})"
            if source["sha256"]:
                line += f"  sha256 {source['sha256']}"
            lines.append(line)
    return "\n".join(lines) + "\n"


def write(data: dict[str, object], out: Path) -> tuple[Path, Path]:
    out.mkdir(parents=True, exist_ok=True)
    as_json = out / MANIFEST_JSON
    as_text = out / MANIFEST_TXT
    as_json.write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8", newline="\n")
    as_text.write_text(render_text(data), encoding="utf-8", newline="\n")
    return as_json, as_text


def download(data: dict[str, object], out: Path) -> int:
    """Fetch every archive into ``out/sources``; return how many failed."""
    folder = out / "sources"
    folder.mkdir(parents=True, exist_ok=True)
    failed = 0
    components = data["components"]
    assert isinstance(components, list)
    for entry in components:
        for source in entry["sources"]:
            try:
                if source["kind"] == "pypi":
                    name_version = source["command"].rsplit(" ", 1)[-1]
                    subprocess.run(
                        [sys.executable, "-m", "pip", "download", "--no-deps"]
                        + ["--no-binary", ":all:", name_version, "-d", str(folder)],
                        check=True,
                    )
                elif source["kind"] == "url" and not source["url"].endswith("/"):
                    target = folder / source["url"].rstrip("/").rsplit("/", 1)[-1]
                    urllib.request.urlretrieve(source["url"], target)  # noqa: S310 - https only
                    print(f"  fetched {target.name}")
            except Exception as error:  # noqa: BLE001 - report every miss, keep going
                failed += 1
                print(f"  FAILED {source['label']}: {error}", file=sys.stderr)
    return failed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--product", default="", help="catalogue product key (default: all)")
    parser.add_argument("--build-dir", type=Path, help="the runtime or app build folder")
    parser.add_argument("--out", type=Path, required=True, help="where to write the manifest")
    parser.add_argument("--commit", default="", help="QUILL release commit (default: HEAD)")
    parser.add_argument(
        "--download", action="store_true", help="also fetch every source archive (network)"
    )
    args = parser.parse_args(argv)
    catalogue = load_catalogue()
    product = args.product or None
    if product and product not in catalogue.products:
        print(f"Unknown product {product!r}; choose from {', '.join(catalogue.products)}.")
        return 2
    if args.build_dir is not None and not args.build_dir.is_dir():
        print(f"No build folder at {args.build_dir}; versions come from the catalogue.")
    entries = collect(catalogue, product, args.build_dir)
    data = manifest(
        entries, product=product, commit=args.commit or release_commit(), build_dir=args.build_dir
    )
    as_json, as_text = write(data, args.out)
    print(f"{len(entries)} copyleft components; manifest {as_json}; list {as_text}")
    if args.download:
        failed = download(data, args.out)
        if failed:
            print(f"{failed} archive(s) could not be fetched; see above.")
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
