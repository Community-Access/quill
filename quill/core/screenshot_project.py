"""Nondestructive screenshot edits, comparisons and portable evidence exports.

Operations use image-relative percentages so callers can offer named regions
without requiring knowledge of desktop pixels. No UI, network or model engine.
"""

from __future__ import annotations

import copy
import hashlib
import html
import io
import json
import math
import uuid
import zipfile
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from PIL.Image import Image as PillowImage

from quill.core.storage import read_json, write_json_atomic
from quill.core.studio_capture import CaptureEvidence, save_capture_report, verify_capture

MAX_PIXELS = 40_000_000
KINDS = ("rectangle", "arrow", "highlight", "spotlight", "text", "redact")


def checked_image(evidence: CaptureEvidence) -> PillowImage:
    from PIL import Image

    raw = Path(evidence.path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != evidence.sha256:
        raise ValueError("The source image changed. Reopen it before continuing.")
    image = Image.open(io.BytesIO(raw))
    if image.width * image.height > MAX_PIXELS:
        raise ValueError("Image exceeds the 40-million-pixel editing limit.")
    image.load()
    converted = image.convert("RGB")
    converted.info.clear()  # Exports must not inherit hidden source EXIF/text metadata.
    return converted


def percent_box(values: Sequence[float], size: tuple[int, int]) -> tuple[int, int, int, int]:
    """Validate percentages and return an exclusive-edge image rectangle."""
    if len(values) != 4 or not all(math.isfinite(float(v)) for v in values):
        raise ValueError("Choose four finite percentage values.")
    x, y, width, height = (float(v) for v in values)
    if x < 0 or y < 0 or width <= 0 or height <= 0 or x + width > 100 or y + height > 100:
        raise ValueError("The region must have positive size and fit within the image.")
    w, h = size
    left, top = round(w * x / 100), round(h * y / 100)
    right, bottom = round(w * (x + width) / 100), round(h * (y + height) / 100)
    if right <= left or bottom <= top:
        raise ValueError("The selected region is smaller than one image dot. Choose a larger area.")
    return left, top, right, bottom


@dataclass
class ScreenshotProject:
    evidence: CaptureEvidence
    operations: list[dict[str, Any]] = field(default_factory=list)
    undo_states: list[list[dict[str, Any]]] = field(default_factory=list, repr=False)
    redo_states: list[list[dict[str, Any]]] = field(default_factory=list, repr=False)
    goal: str = ""
    steps: str = ""
    review: dict[str, str] = field(default_factory=dict)

    def add(self, kind: str, **parameters: Any) -> None:
        if len(self.operations) >= 200:
            raise ValueError("This project has 200 edits. Export a copy before making more.")
        previous = copy.deepcopy(self.operations)
        operation = {"id": uuid.uuid4().hex, "kind": kind, **parameters}
        self.operations.append(operation)
        try:
            self.render()  # Reject invalid operations before committing the edit.
        except Exception:
            self.operations.pop()
            raise
        self.undo_states.append(previous)
        self.redo_states.clear()
        self.review.clear()  # An earlier review never approves a newly edited artifact.

    def undo(self) -> bool:
        if not self.undo_states:
            return False
        self.redo_states.append(copy.deepcopy(self.operations))
        self.operations = self.undo_states.pop()
        self.review.clear()
        return True

    def redo(self) -> bool:
        if not self.redo_states:
            return False
        self.undo_states.append(copy.deepcopy(self.operations))
        self.operations = self.redo_states.pop()
        self.review.clear()
        return True

    def remove(self, index: int) -> None:
        if not 0 <= index < len(self.operations):
            raise ValueError("Select an edit first.")
        self.undo_states.append(copy.deepcopy(self.operations))
        self.operations.pop(index)
        self.redo_states.clear()
        self.review.clear()

    def move(self, index: int, dx: float = 0, dy: float = 0, grow: float = 0) -> None:
        if not 0 <= index < len(self.operations):
            raise ValueError("Select an edit first.")
        previous = copy.deepcopy(self.operations)
        operation = self.operations[index]
        box = operation.get("box")
        if box is None:
            raise ValueError("This operation has no position. Undo it and choose another size.")
        x, y, width, height = box
        operation["box"] = (x + dx, y + dy, width + grow, height + grow)
        try:
            self.render()
        except Exception:
            self.operations = previous
            raise
        self.undo_states.append(previous)
        self.redo_states.clear()
        self.review.clear()

    def render(self) -> PillowImage:
        from PIL import Image, ImageDraw, ImageFont

        image = checked_image(self.evidence)
        for number, operation in enumerate(self.operations, 1):
            kind = operation["kind"]
            if kind == "resize":
                width, height = int(operation["width"]), int(operation["height"])
                if min(width, height) < 1 or width * height > MAX_PIXELS:
                    raise ValueError("Resize must be positive and at most 40 million image dots.")
                image = image.resize((width, height), Image.Resampling.LANCZOS)
                continue
            box = percent_box(operation.get("box", (0, 0, 100, 100)), image.size)
            if kind == "crop":
                image = image.crop(box)
                continue
            if kind not in KINDS:
                raise ValueError("Unknown image operation.")
            left, top, right, bottom = box
            # Pillow draws inclusive edges; never paint outside the selected area.
            rect = (left, top, right - 1, bottom - 1)
            color = operation.get("color", "#ffff00")
            stroke = max(2, min(image.size) // 150)
            draw = ImageDraw.Draw(image)
            if kind == "redact":
                draw.rectangle(rect, fill="black")  # Solid, flattened and irreversible in export.
                continue
            if kind == "spotlight":
                shade = Image.new("RGB", image.size, "black")
                shade = Image.blend(image, shade, 0.65)
                shade.paste(image.crop(box), (left, top))
                image = shade
            elif kind == "highlight":
                patch = Image.new("RGB", (right - left, bottom - top), color)
                image.paste(Image.blend(image.crop(box), patch, 0.35), (left, top))
            elif kind == "arrow":
                draw.line((left, bottom - 1, right - 1, top), fill=color, width=stroke)
                tip = max(4, min(right - left, bottom - top) // 4)
                draw.polygon(
                    [
                        (right - 1, top),
                        (right - 1 - tip, top),
                        (right - 1, min(bottom - 1, top + tip)),
                    ],
                    fill=color,
                )
            elif kind == "rectangle":
                draw.rectangle(rect, outline=color, width=stroke)
            text = str(operation.get("text", "")).strip()
            # Every visible annotation has a stable number, independent of colour.
            label = f"{number}. {text}" if text else str(number)
            font = ImageFont.load_default(size=max(12, min(48, image.height // 30)))
            draw = ImageDraw.Draw(image)
            label_box = draw.textbbox((left, top), label, font=font)
            if label_box[2] > image.width or label_box[3] > image.height:
                raise ValueError("The annotation label does not fit. Shorten it or move it inward.")
            draw.rectangle(label_box, fill="black")
            draw.text((left, top), label, fill="white", font=font)
        return image

    def describe(self, *, simple: bool = False) -> str:
        if simple:
            names = {
                "crop": "Keep selected area",
                "redact": "Hide private information",
                "rectangle": "Numbered box",
                "arrow": "Arrow",
                "text": "Text note",
                "highlight": "Highlight",
                "spotlight": "Spotlight",
                "resize": "Change size",
            }
            return (
                "Original kept unchanged.\n"
                + "\n".join(
                    f"{i}. {names.get(item['kind'], item['kind'])}: {item.get('text', '')}"
                    for i, item in enumerate(self.operations, 1)
                )
                + "\nReview the result before sharing."
            )
        lines = [f"Source: {self.evidence.target}", f"Original SHA-256: {self.evidence.sha256}"]
        for number, operation in enumerate(self.operations, 1):
            lines.append(
                f"{number}. {operation['kind']}: "
                + ", ".join(
                    f"{key}={value}"
                    for key, value in operation.items()
                    if key not in {"kind", "id"}
                )
            )
        lines += [
            "Original remains unchanged. Exported redactions are solid flattened rectangles.",
            "Review every sensitive area; the program cannot prove all private text is masked.",
        ]
        return "\n".join(lines)

    def save(self, path: Path) -> None:
        checked_image(self.evidence)
        write_json_atomic(
            path,
            {
                "schema_version": 1,
                "source": asdict(self.evidence),
                "operations": self.operations,
                "goal": self.goal,
                "steps": self.steps,
                "review": self.review,
            },
        )

    @classmethod
    def load(cls, path: Path) -> ScreenshotProject:
        raw = read_json(path, {})
        if not isinstance(raw, dict) or raw.get("schema_version") != 1:
            raise ValueError("Unsupported screenshot project.")
        source = raw.get("source", {})
        source_path = Path(str(source.get("path", "")))
        if str(source_path).startswith(("\\\\", "//")) or not source_path.is_absolute():
            raise ValueError("Project sources must be local absolute image paths.")
        # A shared project may not make the app open an arbitrary remote/local source.
        if source_path.resolve().parent != path.resolve().parent:
            raise ValueError("Place the project beside its original image before opening it.")
        evidence = verify_capture(
            Path(source["path"]),
            str(source.get("target", "Saved image")),
            expected_sha256=str(source["sha256"]),
        )
        # Only known evidence fields; a project never executes network or command data.
        evidence = replace(
            evidence,
            metadata=source.get("metadata", {}),
            captured_at=str(source.get("captured_at", evidence.captured_at)),
        )
        operations = raw.get("operations", [])
        if not isinstance(operations, list) or len(operations) > 200:
            raise ValueError("Invalid project operations or more than 200 edits.")
        for operation in operations:
            if not isinstance(operation, dict):
                raise ValueError("Invalid project operation.")
            if "box" in operation:
                operation["box"] = tuple(operation["box"])
        project = cls(
            evidence,
            operations=operations,
            goal=str(raw.get("goal", "")),
            steps=str(raw.get("steps", "")),
        )
        project.render()
        # Imported review is not trusted approval to publish or share.
        return project

    def export(self, folder: Path, image_format: str = "PNG") -> CaptureEvidence:
        if image_format not in {"PNG", "JPEG", "WEBP"}:
            raise ValueError("Choose PNG, JPEG or WEBP.")
        image = self.render()
        folder.mkdir(parents=True, exist_ok=True)
        suffix = {"PNG": ".png", "JPEG": ".jpg", "WEBP": ".webp"}[image_format]
        destination = folder / ("studio-edited-" + uuid.uuid4().hex + suffix)
        image.save(destination, format=image_format)
        evidence = verify_capture(destination, "Edited screenshot")
        evidence = replace(
            evidence,
            metadata={
                "parent_sha256": self.evidence.sha256,
                "operations": self.public_operations(),
                "goal": self.goal,
                "steps": self.steps,
                "review": self.review,
                "original_included": False,
            },
        )
        save_capture_report(
            evidence,
            observations=(
                "Edited image exported. Original excluded. "
                "Review content and privacy before sharing. Historical text is omitted."
            ),
        )
        return evidence

    def public_operations(self) -> list[dict[str, Any]]:
        # A later redaction can hide earlier annotation text. Keep historical
        # text only in the private layered project, never in shareable exports.
        return [
            {key: value for key, value in operation.items() if key != "text"}
            for operation in self.operations
        ]

    def bundle(self, folder: Path, *, strict: bool = False, waiver: str = "") -> Path:
        if strict and not all(self.review.get(key) == "reviewed" for key in ("privacy", "content")):
            if not waiver.strip():
                raise ValueError("Strict export needs privacy/content review or a recorded waiver.")
        evidence = self.export(folder)
        manifest: dict[str, Any] = {
            "schema_version": 1,
            "export": asdict(evidence),
            "goal": self.goal,
            "steps_to_reproduce": self.steps,
            "review": self.review,
            "waiver": waiver,
            "original_included": False,
            "semantic_status": "Needs human judgment",
            "annotations": self.public_operations(),
        }
        # Omit original file paths and source text that could defeat a visual redaction.
        manifest["export"]["path"] = Path(evidence.path).name
        manifest["export"]["metadata"] = {"parent_sha256": self.evidence.sha256}
        text = (
            f"Goal: {self.goal}\nSteps: {self.steps}\n"
            f"Export SHA-256: {evidence.sha256}\n"
            "File decode and hash verified. Privacy/completeness need human judgment.\n"
            f"Review: {self.review}\nWaiver: {waiver}\n"
        )
        destination = folder / ("studio-evidence-" + uuid.uuid4().hex + ".zip")
        exported_bytes = Path(evidence.path).read_bytes()
        if hashlib.sha256(exported_bytes).hexdigest() != evidence.sha256:
            raise ValueError("The export changed before packaging. Export it again.")
        with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("screenshot.png", exported_bytes)
            archive.writestr("evidence.json", json.dumps(manifest, ensure_ascii=False, indent=2))
            archive.writestr("description.md", text)
            archive.writestr(
                "description.html",
                "<!doctype html><html lang='en'><head>"
                "<meta charset='utf-8'><title>Screenshot evidence</title></head>"
                "<body><main><h1>Screenshot evidence</h1><pre>"
                + html.escape(text)
                + "</pre></main></body></html>",
            )
        return destination


def compare_screenshots(first: CaptureEvidence, second: CaptureEvidence) -> dict[str, Any]:
    from PIL import ImageChops, ImageStat

    a, b = checked_image(first), checked_image(second)
    if a.size != b.size:
        return {
            "same_dimensions": False,
            "first_size": a.size,
            "second_size": b.size,
            "status": "Not comparable without deliberate resizing",
        }
    difference = ImageChops.difference(a, b)
    # Pixel count, rather than a model's judgment that two screens look alike.
    channels = difference.split()
    mask = ImageChops.lighter(ImageChops.lighter(channels[0], channels[1]), channels[2])
    changed = sum(mask.histogram()[1:])
    return {
        "same_dimensions": True,
        "changed_pixels": changed,
        "changed_percent": 100 * changed / (a.width * a.height),
        "bounding_box": difference.getbbox(),
        "mean_channel_difference": ImageStat.Stat(difference).mean,
        "first_sha256": first.sha256,
        "second_sha256": second.sha256,
        "status": "Pixel difference measured; meaning needs judgment",
    }
