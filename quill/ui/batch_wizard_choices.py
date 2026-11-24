"""The choices the batch-conversion wizard's pages read and write.

Moved out of :mod:`quill.ui.batch_wizard_pages` (GATE-11) unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from quill.core.batch_convert import OutputLayout, OverwritePolicy


@dataclass
class _WizardChoices:
    """Mutable container that pages read and write."""

    root: Path
    recursive: bool
    output_layout: OutputLayout
    overwrite: OverwritePolicy
    direction: str  # "import" or "export"
    source_format: str
    target_format: str
    profile: str | None
