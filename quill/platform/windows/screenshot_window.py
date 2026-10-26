"""Render the selected window into its own bitmap, without sampling other windows."""

from __future__ import annotations

import ctypes

from quill.platform.windows.screen_capture import ScreenCaptureError


def render_window(handle):
    import win32gui
    import win32ui
    from PIL import Image

    user32 = ctypes.windll.user32
    user32.IsHungAppWindow.argtypes = [ctypes.c_void_p]
    user32.IsHungAppWindow.restype = ctypes.c_bool
    if user32.IsHungAppWindow(handle):
        raise ScreenCaptureError(
            "The selected application is not responding. Try again after it recovers."
        )
    left, top, right, bottom = win32gui.GetWindowRect(handle)
    width, height = right - left, bottom - top
    if min(width, height) <= 0 or width * height > 40_000_000:
        raise ScreenCaptureError("This window has no usable capture size or is too large.")
    window_dc = win32gui.GetWindowDC(handle)
    source = win32ui.CreateDCFromHandle(window_dc)
    memory = source.CreateCompatibleDC()
    bitmap = win32ui.CreateBitmap()
    try:
        bitmap.CreateCompatibleBitmap(source, width, height)
        memory.SelectObject(bitmap)
        user32.PrintWindow.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint]
        user32.PrintWindow.restype = ctypes.c_bool
        if not user32.PrintWindow(handle, memory.GetSafeHdc(), 0):
            raise ScreenCaptureError(
                "The selected window did not provide its image. No desktop fallback was used."
            )
        info = bitmap.GetInfo()
        if info["bmBitsPixel"] != 32:
            raise ScreenCaptureError("The selected window returned an unsupported bitmap format.")
        return Image.frombuffer(
            "RGB",
            (width, height),
            bitmap.GetBitmapBits(True),
            "raw",
            "BGRX",
            0,
            1,
        )
    finally:
        memory.DeleteDC()
        source.DeleteDC()
        win32gui.ReleaseDC(handle, window_dc)
        win32gui.DeleteObject(bitmap.GetHandle())
