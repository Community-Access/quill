"""Optional native UIA provider bridge for the Table Studio grid.

Thin wrapper over the compiled ``_quill_table_uia`` extension (built from
``quill/native/table_uia``). When the ``.pyd`` is present this gives the grid a
real Windows UI Automation ``ITableProvider`` with cell-level focus/value/
structure events; when it is absent everything here no-ops and the grid uses the
``wx.Accessible`` MSAA fallback in :mod:`quill.ui.table_studio_accessible`.

The provider is a pure enhancement — QUILL never requires it. All calls are
best-effort and never raise into the UI.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


def _load_module() -> Any | None:
    """The compiled provider, from site-packages or the source tree.

    A shipped build stages the ``.pyd`` into site-packages
    (``scripts/build_windows_distribution._stage_table_uia``), so the plain
    import finds it and users get the real provider.

    A **source checkout** did not. ``scripts/build_table_uia.py`` writes the
    ``.pyd`` into ``quill/native/table_uia/`` (it is gitignored, so it exists
    only where somebody built it) -- and that directory is not on ``sys.path``,
    so the import failed even *after* running the documented build step. The
    grid silently used the MSAA fallback and nothing said otherwise.

    Shipped builds were unaffected, which is what made it easy to miss: it
    meant *nobody developing QUILL ever exercised the native path*, so a
    regression in the C++ or in the pybind11 bridge could only be found by a
    release build or by somebody using one. The fallback exists to cover a
    machine with no compiled module, not to hide the module from its authors.

    So a checkout now loads it directly from the source tree, which makes
    building it actually pay off. Still entirely optional: no ``.pyd``, no
    provider, MSAA exactly as before.
    """
    try:
        import _quill_table_uia  # type: ignore[import-not-found]

        return _quill_table_uia
    except Exception:  # noqa: BLE001 - absent/incompatible => try the source tree
        pass
    return _load_from_source_tree()


def _load_from_source_tree() -> Any | None:
    """Import a locally built ``.pyd`` out of ``quill/native/table_uia``."""
    import importlib.util
    from pathlib import Path

    native_dir = Path(__file__).resolve().parent.parent / "native" / "table_uia"
    try:
        candidate = next(native_dir.glob("_quill_table_uia*.pyd"), None)
    except OSError:  # noqa: BLE001 - an unreadable tree is simply no module
        return None
    if candidate is None:
        return None
    try:
        spec = importlib.util.spec_from_file_location("_quill_table_uia", candidate)
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except Exception:  # noqa: BLE001 - a wrong-ABI .pyd => MSAA fallback
        return None
    # Register it so a later plain ``import _quill_table_uia`` finds the same
    # object rather than loading a second copy of a module that owns COM state.
    import sys

    sys.modules.setdefault("_quill_table_uia", module)
    return module


_MODULE = _load_module()


def is_available() -> bool:
    """True when the compiled native UIA provider is importable."""
    return _MODULE is not None


class NativeUiaProvider:
    """A live native UIA provider attached to one grid ``hwnd``.

    Construct via :func:`attach`; call :meth:`notify_focus` on cell moves,
    :meth:`notify_structure` on row/column changes, and :meth:`notify_value` on
    edits. :meth:`detach` releases it. Every method is a no-op when the native
    module is unavailable.
    """

    def __init__(self, handle: int | None) -> None:
        self._handle = handle

    @property
    def active(self) -> bool:
        return self._handle is not None and _MODULE is not None

    def notify_focus(self, row: int, col: int) -> None:
        if not self.active:
            return
        try:
            _MODULE.notify_focus(self._handle, row, col)
        except Exception:  # noqa: BLE001 - never break navigation
            pass

    def notify_structure(self) -> None:
        if not self.active:
            return
        try:
            _MODULE.notify_structure(self._handle)
        except Exception:  # noqa: BLE001
            pass

    def notify_value(self, row: int, col: int, new_value: str) -> None:
        if not self.active:
            return
        try:
            _MODULE.notify_value(self._handle, row, col, new_value)
        except Exception:  # noqa: BLE001
            pass

    def detach(self) -> None:
        if self._handle is None or _MODULE is None:
            return
        try:
            _MODULE.detach(self._handle)
        except Exception:  # noqa: BLE001
            pass
        self._handle = None


def attach(
    hwnd: int,
    *,
    get_dims: Callable[[], tuple[int, int]],
    get_value: Callable[[int, int], str],
    get_col_header: Callable[[int], str],
    get_row_header: Callable[[int], str],
    get_focus: Callable[[], tuple[int, int]],
    set_focus: Callable[[int, int], None],
    is_editable: Callable[[int, int], bool],
    caption: str,
) -> NativeUiaProvider | None:
    """Attach the native provider to ``hwnd``; ``None`` when unavailable."""
    if _MODULE is None:
        return None
    try:
        handle = _MODULE.attach(
            hwnd,
            get_dims,
            get_value,
            get_col_header,
            get_row_header,
            get_focus,
            set_focus,
            is_editable,
            caption,
        )
    except Exception:  # noqa: BLE001 - attach failure => MSAA fallback
        return None
    return NativeUiaProvider(handle)


__all__ = ["NativeUiaProvider", "attach", "is_available"]
