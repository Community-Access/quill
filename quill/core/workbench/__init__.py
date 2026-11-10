"""The shared Workbench engine: wx-free tables both providers fill in.

GitHub and WordPress are two providers of one Workbench (GitHub PRD section 10,
WordPress PRD section 3). Everything here is provider-neutral data and the
rules over it; ``quill/core/github/workbench_*`` and, later,
``quill/core/wordpress/workbench_*`` hold only what is particular to each, and
``quill/ui/workbench_frame.py`` is the one window that shows them.

- :mod:`.tree`: the Navigator as data (``NodeSpec``, ``TreeSpec``).
- :mod:`.actions`: what can be done to each row type, and the context-menu rules.
- :mod:`.properties`: Properties sheets, mixed values, and the diff of a save.
- :mod:`.filters`: one query string, its attributes and operators.
- :mod:`.history`: Change History and the undo stack.
- :mod:`.help`: authored help records, keyed by node, command or field.
- :mod:`.coverage`: which provider operations have a home, and which do not yet.
"""

from __future__ import annotations

from quill.core.error_codes import CodedError

__all__ = ["WorkbenchSpecError"]


class WorkbenchSpecError(CodedError, ValueError):
    """A provider's table breaks one of the engine's rules (a bad key, parent or row)."""

    code = "QUILL-WORKBENCH-SPEC-INVALID"
