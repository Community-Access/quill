"""Compile a project's manuscript into one document (wx-free).

Walks the manuscript spine in order, strips each file's front matter, and joins
the bodies with a separator. The result is plain text suitable for QUILL's
existing export pipeline (``quill/io/export.py``) — Story Studio adds no new
export engine, it only decides *what* prose goes in and in *what* order.
"""

from __future__ import annotations

from collections.abc import Callable

from quill.core.story.frontmatter import split_front_matter
from quill.core.story.model import StoryProject

__all__ = ["compile_manuscript"]


def compile_manuscript(
    project: StoryProject,
    read_text: Callable[[str], str],
    *,
    separator: str = "\n\n",
) -> str:
    """Return the manuscript files joined in order, front matter removed."""
    bodies = [split_front_matter(read_text(path))[1] for path in project.manuscript]
    return separator.join(bodies)
