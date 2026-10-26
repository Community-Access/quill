"""Cancelable bounded still sequences and overlap-verified vertical stitching."""

from __future__ import annotations

import uuid
from collections.abc import Callable, Sequence
from dataclasses import replace
from pathlib import Path

from quill.core.screenshot_project import MAX_PIXELS, checked_image
from quill.core.storage import write_json_atomic
from quill.core.studio_capture import (
    CaptureEvidence,
    CaptureTarget,
    save_capture_report,
    verify_capture,
)
from quill.stability.task_manager import CancellationToken


def capture_sequence(
    capture: Callable[[Path, CaptureTarget], CaptureEvidence],
    target: CaptureTarget,
    folder: Path,
    count: int,
    interval: float,
    token: CancellationToken,
    progress: Callable[[int, int], None] | None = None,
) -> list[CaptureEvidence]:
    if not 1 <= count <= 30 or not 1 <= interval <= 60:
        raise ValueError("Choose 1–30 screenshots, 1–60 seconds apart.")
    captures = []
    manifest = folder / ("studio-sequence-" + uuid.uuid4().hex + ".json")
    folder.mkdir(parents=True, exist_ok=True)
    try:
        for index in range(count):
            token.raise_if_cancelled()
            if index:
                token.event.wait(interval)
                token.raise_if_cancelled()
            evidence = capture(folder, target)
            save_capture_report(evidence)
            captures.append(evidence)
            write_json_atomic(
                manifest,
                {
                    "status": "In progress",
                    "requested": count,
                    "captured": [{"path": item.path, "sha256": item.sha256} for item in captures],
                },
            )
            if progress:
                progress(index + 1, count)
    except Exception as error:
        write_json_atomic(
            manifest,
            {
                "status": "Incomplete",
                "error": str(error),
                "requested": count,
                "captured": [{"path": e.path, "sha256": e.sha256} for e in captures],
            },
        )
        raise
    write_json_atomic(
        manifest,
        {
            "status": "Complete",
            "requested": count,
            "captured": [{"path": e.path, "sha256": e.sha256} for e in captures],
        },
    )
    return captures


def stitch_vertical(evidence_list: Sequence[CaptureEvidence], folder: Path) -> CaptureEvidence:
    """Only join when full-width overlapping rows match exactly. Otherwise refuse.

    Sticky headers, dynamic content and animations can make stitching impossible;
    callers retain the source screenshots and must report this limitation.
    """
    from PIL import Image, ImageChops

    if not 2 <= len(evidence_list) <= 30:
        raise ValueError("Choose between 2 and 30 screenshots in top-to-bottom order.")
    if sum(item.width * item.height for item in evidence_list) > MAX_PIXELS:
        raise ValueError("This group is too large to combine. Choose fewer or smaller screenshots.")
    images = [checked_image(evidence) for evidence in evidence_list]
    width = images[0].width
    if any(image.width != width for image in images):
        raise ValueError("Screenshots have different widths. They cannot be stitched reliably.")
    strips = [images[0]]
    joins = []
    previous = images[0]
    for current in images[1:]:
        if (
            previous.size == current.size
            and ImageChops.difference(previous, current).getbbox() is None
        ):
            raise ValueError(
                "Two consecutive screenshots are identical; scrolling may not have moved."
            )
        overlap = 0
        # Match hash candidates first; compare the complete candidate before accepting.
        min_overlap = min(32, min(previous.height, current.height) // 3)
        first_row = current.crop((0, 0, width, 1)).tobytes()
        for height in range(min(previous.height, current.height) - 1, max(1, min_overlap) - 1, -1):
            row = previous.height - height
            if previous.crop((0, row, width, row + 1)).tobytes() != first_row:
                continue
            a = previous.crop((0, row, width, previous.height))
            b = current.crop((0, 0, width, height))
            if ImageChops.difference(a, b).getbbox() is None:
                overlap = height
                break
        if not overlap:
            raise ValueError(
                "No reliable overlap found. Source images were retained; no stitch was made."
            )
        strips.append(current.crop((0, overlap, width, current.height)))
        joins.append(overlap)
        previous = current
    height = sum(strip.height for strip in strips)
    if width * height > MAX_PIXELS:
        raise ValueError("The combined image is too large. Stitch a smaller group.")
    output = Image.new("RGB", (width, height))
    top = 0
    for strip in strips:
        output.paste(strip, (0, top))
        top += strip.height
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / ("studio-stitched-" + uuid.uuid4().hex + ".png")
    output.save(path, format="PNG")
    evidence = verify_capture(path, "Combined scrolling screenshots")
    evidence = replace(
        evidence,
        metadata={
            "source_sha256": [e.sha256 for e in evidence_list],
            "matched_overlap_rows": joins,
            "completeness": "Not verified; exact joins do not prove all content was captured",
        },
    )
    save_capture_report(evidence)
    return evidence
