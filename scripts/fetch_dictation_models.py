"""Fetch the dictation models QUILL Lite ships, and verify every byte.

The models are too large to live in git, so a build fetches them: sherpa-onnx's
model releases on GitHub, each file checked against the SHA-256 pinned in
:mod:`quill.core.windows_dictation.engines`. A file that does not match is
deleted and the fetch fails -- a build must never ship a model nobody reviewed.

Idempotent: files already present with the right digest are left alone, so
running it before every build costs a few seconds of hashing.

Usage::

    python scripts/fetch_dictation_models.py                 # -> build/dictation-models
    python scripts/fetch_dictation_models.py --out DIR
    python scripts/fetch_dictation_models.py --check         # verify, fetch nothing
    python scripts/fetch_dictation_models.py --package-out build/dictation-python

``--package-out`` also copies the build interpreter's sherpa-onnx package there,
for an installer whose shared runtime does not carry it (see
``quill.core.windows_dictation.engines.package_dirs``).
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))

from quill.core.windows_dictation.engines import (  # noqa: E402
    ENGINES,
    MODELS_FOLDER,
    VAD_MODEL,
    VAD_URL,
    ModelFile,
)

DEFAULT_OUT = _REPO / "build" / MODELS_FOLDER

#: Written beside the models so the licences travel with them.
_NOTICE = """Speech models bundled with QUILL Lite for dictation.

moonshine-tiny-en  Moonshine tiny, English. Copyright (c) 2024 Useful Sensors.
                   MIT License (moonshine-tiny-en/LICENSE).
whisper-tiny-en    Whisper tiny.en. Copyright (c) 2022 OpenAI. MIT License.
silero_vad.onnx    Silero VAD. Copyright (c) 2020-present Silero Team.
                   MIT License.

All three are converted to ONNX and distributed by the sherpa-onnx project
(k2-fsa/sherpa-onnx, Apache License 2.0), which also runs them.
"""


def _digest(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            sha.update(block)
    return sha.hexdigest()


def _good(path: Path, item: ModelFile) -> bool:
    return path.is_file() and _digest(path) == item.sha256


def _download(url: str, target: Path) -> None:
    print(f"  downloading {url}")
    request = urllib.request.Request(url, headers={"User-Agent": "QUILL build"})
    with urllib.request.urlopen(request, timeout=300) as response, target.open("wb") as out:  # noqa: S310
        shutil.copyfileobj(response, out)


def fetch(out: Path, *, check_only: bool = False) -> list[str]:
    """Make *out* hold every model file. Returns the problems, empty on success."""
    problems: list[str] = []
    out.mkdir(parents=True, exist_ok=True)

    vad = out / VAD_MODEL.name
    if not _good(vad, VAD_MODEL):
        if check_only:
            problems.append(f"{vad.name} missing or wrong")
        else:
            _download(VAD_URL, vad)
            if not _good(vad, VAD_MODEL):
                vad.unlink(missing_ok=True)
                problems.append(f"{vad.name}: digest mismatch")

    for engine in ENGINES:
        if not engine.folder:
            continue
        folder = out / engine.folder
        missing = [item for item in engine.files if not _good(folder / item.name, item)]
        if not missing:
            print(f"  {engine.folder}: present")
            continue
        if check_only:
            problems.extend(f"{engine.folder}/{item.name} missing or wrong" for item in missing)
            continue
        folder.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory() as scratch:
            archive = Path(scratch) / "model.tar.bz2"
            _download(engine.archive, archive)
            with tarfile.open(archive, "r:bz2") as tar:
                members = {Path(member.name).name: member for member in tar.getmembers()}
                for item in missing:
                    member = members.get(item.source or item.name)
                    if member is None:
                        problems.append(f"{engine.folder}/{item.name}: not in the archive")
                        continue
                    source = tar.extractfile(member)
                    if source is None:
                        problems.append(f"{engine.folder}/{item.name}: not a file")
                        continue
                    with (folder / item.name).open("wb") as target:
                        shutil.copyfileobj(source, target)
        for item in missing:
            path = folder / item.name
            if path.exists() and not _good(path, item):
                path.unlink()
                problems.append(f"{engine.folder}/{item.name}: digest mismatch")
        print(f"  {engine.folder}: fetched")

    if not check_only:
        (out / "NOTICE.txt").write_text(_NOTICE, encoding="utf-8")
    return problems


def stage_package(out: Path) -> Path:
    """Copy this interpreter's sherpa-onnx package into *out*; return the copy.

    Only the importable package: the ``.lib`` import libraries are for linking
    C++ against it and are never loaded, so they stay behind.
    """
    import sherpa_onnx

    source = Path(sherpa_onnx.__file__).resolve().parent
    target = out / "sherpa_onnx"
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target, ignore=shutil.ignore_patterns("__pycache__", "*.lib"))
    print(f"  sherpa-onnx {getattr(sherpa_onnx, '__version__', '?')} -> {target}")
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--check", action="store_true", help="verify only; fetch nothing")
    parser.add_argument("--package-out", type=Path, help="also stage the sherpa-onnx package here")
    args = parser.parse_args(argv)
    problems = fetch(args.out, check_only=args.check)
    if args.package_out and not problems:
        stage_package(args.package_out)
    if problems:
        print("Dictation models are not complete:\n  " + "\n  ".join(problems))
        return 1
    print(f"Dictation models ready in {args.out}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
