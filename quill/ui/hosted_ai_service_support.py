"""Background-task and UI-thread helpers for hosted AI."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

__all__ = ["_call_after", "_submit"]


def _call_after(func: Callable[..., None], *args: Any) -> None:
    import wx

    wx.CallAfter(func, *args)


def _submit(name: str, func: Callable[..., Any], *, on_success: Any, on_failure: Any) -> None:
    """Submit one background job through the shared worker helper."""
    from quill.ui.update_download import thread_submit

    thread_submit(name, func, on_success=on_success, on_failure=on_failure)
