"""Spoken opening and closing credits for an assembled audiobook.

The standard audiobook frame, synthesized with the run's own voice and
prepended/appended as the book's first and last chapters:

    "<Title>. Written by <Author>. Narrated by <Narrator>."
    "This has been <Title>. Thank you for listening."

wx-free, strict-typed. The texts are pure functions (unit-tested); synthesis
rides the existing document pipeline over a temp text file, so pronunciation
dictionaries, normalization, and the engine's shaping all apply.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def opening_credit_text(title: str, author: str = "", narrator: str = "") -> str:
    """The opening announcement, in plain sentences (empty fields drop out)."""
    parts = [f"{title.strip()}."]
    if author.strip():
        parts.append(f"Written by {author.strip()}.")
    if narrator.strip():
        parts.append(f"Narrated by {narrator.strip()}.")
    return " ".join(parts)


def closing_credit_text(title: str) -> str:
    """The closing announcement."""
    return f"This has been {title.strip()}. Thank you for listening."


def synthesize_credit_files(
    title: str,
    author: str,
    narrator: str,
    spec: Any,
    options: Any,
    work_dir: Path,
) -> tuple[Path, Path]:
    """Synthesize the two credit chapters as WAVs under *work_dir*.

    Returns ``(opening_wav, closing_wav)``. Raises the pipeline's own errors on
    failure — the caller treats credits as best-effort and logs a note.
    """
    from quill.core.speech.document_speech import synthesize_document_to_chaptered_file

    work_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    for stem, text in (
        ("Opening credits", opening_credit_text(title, author, narrator)),
        ("Closing credits", closing_credit_text(title)),
    ):
        source = work_dir / f"{stem}.txt"
        source.write_text(text + "\n", encoding="utf-8")
        out_wav = work_dir / f"{stem}.wav"
        synthesize_document_to_chaptered_file(
            source, out_wav, spec, options, work_dir=work_dir / f"w_{stem}"
        )
        outputs.append(out_wav)
    return outputs[0], outputs[1]
