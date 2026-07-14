"""Table Studio and CSV Studio — accessible structured-table editing.

The wx-free core: a format-neutral table model, a navigation/announcement
controller with a spoken-cell formatter, and CSV/Markdown/HTML I/O. The UI
(``quill/ui/table_studio.py``) renders this on a virtual ``wx.ListCtrl`` with
cell-level accessibility. Ported from the ``table_studio_proto`` prototype.

Both surfaces are experimental opt-ins (Preferences > Experimental).
"""

from __future__ import annotations

from quill.core.table_studio.controller import SpokenCellFormatter, TableController
from quill.core.table_studio.model import (
    Alignment,
    AnnounceConfig,
    Change,
    ContentKind,
    TableCell,
    TableColumn,
    TableDocumentModel,
    TableRow,
)

__all__ = [
    "Alignment",
    "AnnounceConfig",
    "Change",
    "ContentKind",
    "SpokenCellFormatter",
    "TableCell",
    "TableColumn",
    "TableController",
    "TableDocumentModel",
    "TableRow",
]
