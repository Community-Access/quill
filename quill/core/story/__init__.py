"""Story Studio — wx-free domain logic for organizing long-form projects.

A *story project* is an ordinary folder of plain-text files plus an advisory
``project.quillstory.json`` sidecar. This package owns the model, front-matter
codec, heading-derived manuscript structure, sidecar persistence, binder-tree
assembly, and manuscript compilation. It imports no ``wx`` and is strict-typed;
all file IO is injected as callables so the core stays pure and testable.

Convenience re-exports below; submodules may also be imported directly. The
canonical specification is PRD section 5.89c (Story Studio).
"""

from __future__ import annotations

from quill.core.story.binder import BinderNode, build_binder
from quill.core.story.compile import compile_manuscript
from quill.core.story.fields import FieldRow, FieldSpec, build_rows, collect_fields
from quill.core.story.frontmatter import join_front_matter, split_front_matter
from quill.core.story.manuscript import Heading, iter_headings
from quill.core.story.model import ElementKind, StoryElement, StoryProject, new_element
from quill.core.story.storage import PROJECT_FILENAME, load_project, save_project

__all__ = [
    "PROJECT_FILENAME",
    "BinderNode",
    "ElementKind",
    "FieldRow",
    "FieldSpec",
    "Heading",
    "StoryElement",
    "StoryProject",
    "build_binder",
    "build_rows",
    "collect_fields",
    "compile_manuscript",
    "iter_headings",
    "join_front_matter",
    "load_project",
    "new_element",
    "save_project",
    "split_front_matter",
]
