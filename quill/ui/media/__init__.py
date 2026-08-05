"""wxPython shell for the QUILL Media Player (``player.md``).

Phase 2 UI, built on the pure ``quill.core.media`` layer and the shared UI
helpers (``dialog_contract``, ``app_shell``, the reused ``PlayerPanel``). All
accessibility follows the Desktop Accessibility Specialist's checklist: correct
Name/Role/Value/State, focus management, the ``_show_modal_dialog`` contract, and
announcements via ``quill.core.announce``.
"""

from __future__ import annotations
