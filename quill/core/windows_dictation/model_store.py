"""Where downloaded speech models live, and getting, checking and removing them.

**One folder for the family**, so a model downloaded in QUILL Lite is there for
QUILL on the same computer, and the other way round:

* An installed copy: ``%LOCALAPPDATA%\\QuillVille\\Dictation\\models`` --
  local, not roaming, because a 700 MB model has no business following a
  domain user from computer to computer.
* A portable copy: ``<portable folder>\\data\\dictation\\models``, found the
  way every other "do not touch the host computer" rule finds it
  (:func:`quill.core.paths.portable_bundle_root`), so the copy stays
  self-contained and its models travel with it on a USB stick.
* ``QUILL_DICTATION_DOWNLOADS`` overrides both, for tests and support.

**Downloading** goes through the one hardened downloader every QUILL download
shares, :func:`quill.core.release_assets.download_verified`: HTTPS only,
retries, mirror fallback, Safe Mode refused, and -- with its ``partial``
argument -- a ``.part`` file kept beside the model, so a cancelled or
interrupted download carries on where it stopped next time. Each file is
checked against its pinned SHA-256 before it takes its real name; a file that
does not match is deleted and the download says so plainly.

**At run time** a model counts as installed when every file is present at its
pinned size. Hashing 700 MB on every start would cost more than it protects:
the bytes were verified when they arrived.

wx-free; network only inside :func:`download`, which a person starts.
"""

from __future__ import annotations

import os
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

from quill.core.error_codes import CodedError
from quill.core.windows_dictation.model_catalog import (
    CATALOGUE,
    DownloadableModel,
    downloadable,
    megabytes,
)

__all__ = [
    "DOWNLOADS_VARIABLE",
    "ModelDownloadError",
    "download",
    "downloads_root",
    "free_space_problem",
    "installed",
    "installed_models",
    "model_folder",
    "remove",
    "remaining_bytes",
]

DOWNLOADS_VARIABLE = "QUILL_DICTATION_DOWNLOADS"
#: Room left over after a download, so the disk is never filled to the last byte.
_SPARE_BYTES = 200_000_000

Progress = Callable[[float, str], None]


class ModelDownloadError(CodedError):
    """A speech model could not be downloaded, checked or removed. The message
    is a sentence a person can act on."""

    code = "QUILL-DICTATION-MODEL-DOWNLOAD"


def downloads_root() -> Path:
    """The folder optional speech models are kept in (not created here)."""
    override = os.environ.get(DOWNLOADS_VARIABLE, "").strip()
    if override:
        return Path(override)
    try:
        from quill.core.paths import portable_bundle_root

        bundle = portable_bundle_root()
    except Exception:  # noqa: BLE001 - no portable answer is an installed copy
        bundle = None
    if bundle is not None:
        return bundle / "data" / "dictation" / "models"
    local = os.environ.get("LOCALAPPDATA", "").strip()
    base = Path(local) if local else Path.home() / ".quillville"
    return base / "QuillVille" / "Dictation" / "models"


def model_folder(model: DownloadableModel) -> Path:
    return downloads_root() / model.folder


def installed(model: DownloadableModel) -> bool:
    """Every file present at its pinned size."""
    folder = model_folder(model)
    try:
        return all((folder / item.name).stat().st_size == item.size for item in model.files)
    except OSError:
        return False


def installed_models() -> list[DownloadableModel]:
    """The downloaded models, in the catalogue's order."""
    return [model for model in CATALOGUE if installed(model)]


def remaining_bytes(model: DownloadableModel) -> int:
    """What is still to come: files not yet complete, less any partial bytes."""
    folder = model_folder(model)
    left = 0
    for item in model.files:
        final = folder / item.name
        if final.is_file() and final.stat().st_size == item.size:
            continue
        part = folder / f"{item.name}.part"
        have = part.stat().st_size if part.is_file() else 0
        left += max(0, item.size - have)
    return left


def _existing_ancestor(path: Path) -> Path:
    for candidate in (path, *path.parents):
        if candidate.exists():
            return candidate
    return path


def free_space_problem(
    model: DownloadableModel, *, usage: Callable[[Path], Any] | None = None
) -> str:
    """Why there is not room for *model* where it would go, or ``""``."""
    root = downloads_root()
    measure = usage or shutil.disk_usage
    try:
        free = int(measure(_existing_ancestor(root)).free)
    except OSError:
        return ""  # an unanswerable drive is tried; the download says if it fills
    needed = remaining_bytes(model) + _SPARE_BYTES
    if free >= needed:
        return ""
    return (
        f"There is not enough free space for {model.name}: it needs about "
        f"{megabytes(needed)} on the drive with {root}, and {megabytes(free)} is free. "
        "Free some space, then try again."
    )


def download(
    model: DownloadableModel,
    *,
    progress: Progress | None = None,
    should_cancel: Callable[[], bool] | None = None,
    fetch: Callable[..., Path] | None = None,
) -> Path:
    """Fetch every file of *model* that is not already here; return its folder.

    Raises :class:`ModelDownloadError` with a sentence, or
    :class:`~quill.core.release_assets.DownloadCancelled` when cancelled (the
    ``.part`` files stay, so the next Download resumes). *fetch* stands in for
    :func:`~quill.core.release_assets.download_verified` in tests.
    """
    from quill.core.release_assets import DownloadCancelled, ReleaseAssetError, download_verified

    fetch = fetch or download_verified
    folder = model_folder(model)
    try:
        folder.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise ModelDownloadError(
            f"The models folder could not be created ({folder}): {error}"
        ) from error
    total = model.download_bytes or 1
    done = 0
    for item in model.files:
        final = folder / item.name
        if final.is_file() and final.stat().st_size == item.size:
            done += item.size
            continue
        offset = done
        part = folder / f"{item.name}.part"
        if part.is_file() and part.stat().st_size >= item.size:
            # Arrived whole last time but was never checked (the program
            # closed): a Range request past the end would only fail.
            if part.stat().st_size == item.size and _sha256(part) == item.sha256:
                part.replace(final)
                done += item.size
                continue
            part.unlink(missing_ok=True)

        def each(
            fraction: float, _message: str, offset: int = offset, size: int = item.size
        ) -> None:
            if progress is not None:
                progress(min(0.99, (offset + fraction * size) / total), f"Downloading {model.name}")

        try:
            fetch(
                model.url(item),
                final,
                sha256=item.sha256,
                progress=each,
                should_cancel=should_cancel,
                label=f"Downloading {model.name}",
                partial=part,
            )
        except DownloadCancelled:
            raise
        except ReleaseAssetError as error:
            said = str(error)
            if "Safe Mode" in said:
                raise ModelDownloadError(
                    "Downloading speech models is turned off in Safe Mode."
                ) from error
            if "Checksum" in said:
                raise ModelDownloadError(
                    f"{model.name} did not download correctly (a file did not match its "
                    "checksum), so it was deleted. Try again; if it keeps happening, the "
                    "file at the source has changed and QUILL needs an update."
                ) from error
            raise ModelDownloadError(
                f"{model.name} could not be downloaded. Check the internet connection and "
                "try again; files that already arrived whole are kept."
            ) from error
        done += item.size
    if progress is not None:
        progress(1.0, f"{model.name} is ready")
    return folder


def _sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def remove(model_id: str) -> None:
    """Delete a downloaded model, partial files and all. Raises
    :class:`ModelDownloadError` with a sentence when Windows will not let go."""
    model = downloadable(model_id)
    if model is None:
        return
    folder = model_folder(model)
    if not folder.exists():
        return
    try:
        shutil.rmtree(folder)
    except OSError as error:
        raise ModelDownloadError(
            f"{model.name} could not be removed, probably because dictation is using it. "
            "Choose another speech engine, close and reopen the program, then remove it."
        ) from error
