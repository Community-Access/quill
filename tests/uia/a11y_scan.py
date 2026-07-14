"""Accessibility scanner for UIA trees: capture what a screen reader would meet.

`scan_window` walks a window's UIA descendants and records, per element, the
control type, the accessible name, and whether it is keyboard focusable. The
records are the regression currency of the UI-automation suite:

- `unnamed_focusable(records)` — the axe-style failure list: anything a user
  can Tab to that has no accessible name is a bug, full stop.
- Snapshots of `summarize(records)` can be committed as baselines so a dialog
  quietly losing a label fails a test instead of a user.
"""

from __future__ import annotations

from dataclasses import dataclass

#: Control types that are structural noise for name auditing (panes, separators).
_UNNAMED_OK = {"Pane", "Separator", "Group", "Custom", "TitleBar", "ScrollBar", "Thumb"}


@dataclass(frozen=True, slots=True)
class A11yRecord:
    control_type: str
    name: str
    focusable: bool
    automation_id: str


def scan_window(window: object, *, max_elements: int = 400) -> list[A11yRecord]:
    """Walk ``window``'s UIA descendants into a flat, order-stable record list."""
    records: list[A11yRecord] = []
    try:
        descendants = window.descendants()  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001 - a vanished window scans as empty
        return records
    for element in descendants[:max_elements]:
        try:
            info = element.element_info
            records.append(
                A11yRecord(
                    control_type=str(info.control_type or ""),
                    name=str(info.name or "").strip(),
                    focusable=bool(getattr(info, "element", None) is not None)
                    and bool(element.is_keyboard_focusable()),
                    automation_id=str(getattr(info, "automation_id", "") or ""),
                )
            )
        except Exception:  # noqa: BLE001 - stale elements are skipped, not fatal
            continue
    return records


def unnamed_focusable(records: list[A11yRecord]) -> list[A11yRecord]:
    """Keyboard-reachable elements with no accessible name — each one is a bug."""
    return [
        record
        for record in records
        if record.focusable and not record.name and record.control_type not in _UNNAMED_OK
    ]


def summarize(records: list[A11yRecord]) -> list[str]:
    """A speakable, diff-friendly one-line-per-element summary."""
    lines = []
    for record in records:
        focus = "focusable" if record.focusable else "static"
        lines.append(f"{record.control_type}: {record.name or '(unnamed)'} [{focus}]")
    return lines
