"""Accessibility settings for QuillBeacon (PRD 29, 44.3).

A small, persisted settings model covering the four user-facing accessibility
levers: announcement verbosity, high-contrast colors, text scaling, and reduced
motion. The model is wx-free so it can be unit-tested and loaded before the UI
is built; the shell applies it to controls.

Settings live in ``a11y.json`` next to the database. They never affect data,
only presentation, so a bad value can be reset without risk.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

Verbosity = Literal["minimal", "normal", "verbose"]
SETTINGS_NAME = "a11y.json"

# Discrete scale steps keep font sizes predictable for screen-reader users who
# set them by keyboard, rather than a free-form slider.
SCALE_STEPS = (0.85, 0.95, 1.0, 1.1, 1.25, 1.5)
DEFAULT_SCALE_INDEX = 2  # 1.0


@dataclass
class A11ySettings:
    verbosity: Verbosity = "normal"
    high_contrast: bool = False
    scale_index: int = DEFAULT_SCALE_INDEX
    reduced_motion: bool = False

    @property
    def text_scale(self) -> float:
        if 0 <= self.scale_index < len(SCALE_STEPS):
            return SCALE_STEPS[self.scale_index]
        return 1.0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> A11ySettings:
        # Clamp/sanitize so a hand-edited file cannot break the UI.
        v = d.get("verbosity", "normal")
        if v not in ("minimal", "normal", "verbose"):
            v = "normal"
        idx = d.get("scale_index", DEFAULT_SCALE_INDEX)
        if not isinstance(idx, int) or not (0 <= idx < len(SCALE_STEPS)):
            idx = DEFAULT_SCALE_INDEX
        return cls(
            verbosity=v,
            high_contrast=bool(d.get("high_contrast", False)),
            scale_index=idx,
            reduced_motion=bool(d.get("reduced_motion", False)),
        )


def settings_path(data_dir: str | Path) -> Path:
    return Path(data_dir) / SETTINGS_NAME


def load(data_dir: str | Path) -> A11ySettings:
    p = settings_path(data_dir)
    if not p.exists():
        return A11ySettings()
    try:
        return A11ySettings.from_dict(json.loads(p.read_text(encoding="utf-8")))
    except Exception:
        return A11ySettings()


def save(data_dir: str | Path, settings: A11ySettings) -> None:
    settings_path(data_dir).write_text(json.dumps(settings.to_dict(), indent=2), encoding="utf-8")


def apply_to_frame(frame, settings: A11ySettings) -> None:
    """Apply high-contrast colors and text scaling to a BeaconFrame.

    Imported lazily (wx) by the shell; kept here so all a11y logic is in one
    place. Reduced motion is recorded on the frame for callers that animate.
    """
    import wx

    frame._a11y = settings
    scale = settings.text_scale
    # Copy the platform default font, then scale it. (wx.Font(int) is not a
    # valid constructor in this build; the Font-copy overload is.)
    base = wx.Font(wx.NORMAL_FONT)
    font = base.Scaled(scale) if hasattr(base, "Scaled") else base

    fg, bg = ("black", "white")
    if settings.high_contrast:
        fg, bg = ("white", "black")

    def _style(ctrl):
        if ctrl is None:
            return
        try:
            ctrl.SetForegroundColour(wx.Colour(fg))
            ctrl.SetBackgroundColour(wx.Colour(bg))
        except Exception:
            pass
        try:
            ctrl.SetFont(font)
        except Exception:
            pass

    for attr in ("search_box", "results", "details", "dest_list", "sort_combo"):
        _style(getattr(frame, attr, None))
    try:
        frame.SetForegroundColour(wx.Colour(fg))
        frame.SetBackgroundColour(wx.Colour(bg))
        frame.Refresh()
    except Exception:
        pass
