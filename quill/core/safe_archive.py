"""Decompression-bomb protection for ZIP-based document formats.

DOCX, XLSX, ODT, PPTX, EPUB, and Pages files are ZIP archives. A small crafted
archive can declare gigabytes of uncompressed content (a "zip bomb"), so this
module opens archives behind a guard that rejects any archive whose total
declared uncompressed size, or whose per-entry compression ratio, exceeds safe
limits before any entry is read.
"""

from __future__ import annotations

import zipfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from quill.core.error_codes import CodedError

# Maximum total uncompressed bytes we are willing to extract from one archive.
MAX_TOTAL_UNCOMPRESSED = 512 * 1024 * 1024  # 512 MiB
# Maximum uncompressed-to-compressed ratio for a single entry. Legitimate
# office documents stay well under this; classic bombs are far above it.
MAX_COMPRESSION_RATIO = 200
# Ignore the ratio check for tiny entries where it is meaningless.
_RATIO_MIN_COMPRESSED = 1024


class DecompressionBombError(CodedError):
    """Raised when an archive's declared expansion exceeds safe limits."""

    code = "QUILL-ARCHIVE-BOMB"


def check_zip_safety(
    archive: zipfile.ZipFile,
    *,
    max_total: int = MAX_TOTAL_UNCOMPRESSED,
    max_ratio: int = MAX_COMPRESSION_RATIO,
) -> None:
    """Validate an open archive's declared sizes before any entry is read."""
    total = 0
    for info in archive.infolist():
        total += info.file_size
        if total > max_total:
            raise DecompressionBombError(
                "Refused to open archive: total uncompressed size exceeds "
                f"{max_total} bytes (possible decompression bomb)."
            )
        if info.compress_size >= _RATIO_MIN_COMPRESSED:
            ratio = info.file_size / info.compress_size
            if ratio > max_ratio:
                raise DecompressionBombError(
                    "Refused to open archive: entry "
                    f"{info.filename!r} has an unsafe compression ratio "
                    f"({ratio:.0f}:1, limit {max_ratio}:1)."
                )


@contextmanager
def open_zip(
    path: str | Path,
    *,
    max_total: int = MAX_TOTAL_UNCOMPRESSED,
    max_ratio: int = MAX_COMPRESSION_RATIO,
) -> Iterator[zipfile.ZipFile]:
    """Open a ZIP archive with decompression-bomb limits enforced up front."""
    with zipfile.ZipFile(path) as archive:
        check_zip_safety(archive, max_total=max_total, max_ratio=max_ratio)
        yield archive
