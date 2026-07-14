from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class Document:
    text: str = ""
    path: Path | None = None
    modified: bool = False
    encoding: str = "utf-8"
    line_ending: str = "\n"
    source_metadata: dict[str, object] = field(default_factory=dict)
    _revision: int = field(default=0, repr=False)

    @property
    def name(self) -> str:
        if self.path is not None:
            return self.path.name
        display_name = str(self.source_metadata.get("display_name", "")).strip()
        if display_name:
            return " ".join(display_name.split())
        return "Untitled"

    @property
    def revision(self) -> int:
        """Monotonic edit counter incremented on each textual change (#341).

        Contract:

        * ``revision`` is incremented exactly once per successful call to
          :meth:`set_text` that actually changes the text (no-op writes do
          not bump the counter).
        * There is no public setter; the counter advances through
          :meth:`set_text` only. Tests that need to force a known revision
          value can construct a :class:`Document` directly with the private
          ``_revision`` field (it is a dataclass field with ``repr=False``)
          or assign ``doc._revision = N`` because Python does not enforce
          the leading-underscore privacy convention.
        * Other state mutations (encoding change, line-ending change,
          path change via :meth:`mark_saved`, source-metadata edit) do not
          bump the counter; only the user-visible text changes.
        * ``revision`` resets to ``0`` on a freshly constructed Document.
        """
        return self._revision

    def set_text(self, value: str) -> None:
        if value == self.text:
            return
        self.text = value
        self.modified = True
        self._revision += 1

    def mark_content_changed(self) -> None:
        """Record a content change that is not visible in the plain text.

        Rich mode (One Editor, Every Format): applying bold via the TOM
        changes the *document* without changing ``text``, so ``set_text``
        would no-op — yet autosave keys on ``revision`` and the title bar on
        ``modified``. This is the sanctioned bump for those formatting-only
        edits.
        """
        self.modified = True
        self._revision += 1

    def mark_saved(self, path: Path | None = None) -> None:
        if path is not None:
            self.path = path
        self.modified = False
