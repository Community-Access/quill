from __future__ import annotations

from types import SimpleNamespace

from quill.core.accessibility_agent import build_plan
from quill.ui.assistant_tools import (
    AccessibilityAgentDialog,
    DiffReviewDialog,
)


class _TextCtrl:
    def __init__(self, value: str) -> None:
        self._value = value

    def GetValue(self) -> str:
        return self._value


class _Status:
    def __init__(self) -> None:
        self.label = ""

    def SetLabel(self, value: str) -> None:
        self.label = value


class _Dialog:
    def __init__(self) -> None:
        self.ended_with: int | None = None

    def EndModal(self, result: int) -> None:
        self.ended_with = result


# Prompt Studio and Agent Center were retired into the unified AI Library; their
# callback tests are removed with the dialogs. Accessibility Tune-Up and the diff
# reviewer remain and are covered below.


class _CheckListBox:
    def __init__(self, checked: set[int]) -> None:
        self._checked = checked

    def IsChecked(self, index: int) -> bool:
        return index in self._checked

    def Check(self, index: int, value: bool = True) -> None:
        if value:
            self._checked.add(index)
        else:
            self._checked.discard(index)


def _make_accessibility_dialog(
    text: str, checked: set[int]
) -> tuple[AccessibilityAgentDialog, list, list[str]]:
    plan = build_plan("doc.md", text, "markdown", "current document")
    dialog = AccessibilityAgentDialog.__new__(AccessibilityAgentDialog)
    dialog._wx = SimpleNamespace(ID_OK=1)
    dialog.plan = plan
    dialog._document_text = text
    dialog.applied = False
    dialog.status = _Status()
    dialog.dialog = _Dialog()
    dialog.step_list = _CheckListBox(checked)
    applied: list = []
    announcements: list[str] = []
    dialog._on_apply = lambda result: applied.append(result)
    dialog._announce = lambda message: announcements.append(message)
    return dialog, applied, announcements


def test_accessibility_agent_apply_routes_checked_steps() -> None:
    text = "#Title\nUtilize the tool in order to begin.\n"
    dialog, applied, announcements = _make_accessibility_dialog(text, checked=set(range(len(text))))

    dialog._on_apply_clicked(object())

    assert dialog.applied is True
    assert len(applied) == 1
    assert applied[0].changed is True
    assert applied[0].text != text
    assert dialog.dialog.ended_with == 1
    assert announcements and "applied" in announcements[0]


def test_accessibility_agent_apply_with_nothing_checked_makes_no_change() -> None:
    text = "#Title\nUtilize the tool in order to begin.\n"
    dialog, applied, announcements = _make_accessibility_dialog(text, checked=set())

    dialog._on_apply_clicked(object())

    assert dialog.applied is False
    assert applied == []
    assert dialog.dialog.ended_with is None
    assert announcements and "no automatic changes" in announcements[0].lower()


# test_new_custom_prompt_moves_focus_and_announces was removed with the Prompt
# Studio dialog (custom-prompt management is now the AI Library Prompts tab).


def test_make_document_accessible_parents_dialog_to_frame() -> None:
    # Issue #134: the Accessibility Tune-Up dialog must be parented to the real
    # wx frame (self.frame), not the MainFrame controller (self), or wx.Dialog
    # gets a non-window parent and the dialog never shows.
    from pathlib import Path

    source = (Path(__file__).resolve().parents[3] / "quill" / "ui" / "main_frame.py").read_text(
        encoding="utf-8"
    )
    assert "AccessibilityAgentDialog(" in source
    call = source.split("AccessibilityAgentDialog(", 1)[1]
    first_arg = call.split(",", 1)[0].strip()
    assert first_arg == "self.frame", first_arg


def _make_diff_dialog(
    original: str, revised: str, checked: set[int]
) -> tuple[DiffReviewDialog, list[str], list[str]]:
    from quill.core.ai.diff_review import build_diff_review

    dialog = DiffReviewDialog.__new__(DiffReviewDialog)
    dialog._wx = SimpleNamespace(ID_OK=1, ID_CANCEL=0)
    dialog.review = build_diff_review(original, revised)
    dialog.applied = False
    dialog.status = _Status()
    dialog.dialog = _Dialog()
    dialog.hunk_list = _CheckListBox(checked)
    applied: list[str] = []
    announcements: list[str] = []
    dialog._on_apply = lambda text: applied.append(text)
    dialog._announce = lambda message: announcements.append(message)
    return dialog, applied, announcements


def test_diff_review_apply_all_checked_applies_revised() -> None:
    dialog, applied, announcements = _make_diff_dialog("a\nb\nc", "a\nB\nc\nd", checked={0, 1})

    dialog._on_apply_clicked(object())

    assert dialog.applied is True
    assert applied == ["a\nB\nc\nd"]
    assert dialog.dialog.ended_with == 1
    assert announcements and "Applied" in announcements[0]


def test_diff_review_partial_apply_keeps_rejected_hunk() -> None:
    # Accept only the first hunk (change b->B); reject the appended line.
    dialog, applied, announcements = _make_diff_dialog("a\nb\nc", "a\nB\nc\nd", checked={0})

    dialog._on_apply_clicked(object())

    assert dialog.applied is True
    assert applied == ["a\nB\nc"]
    assert dialog.dialog.ended_with == 1


def test_diff_review_reject_all_makes_no_change() -> None:
    dialog, applied, announcements = _make_diff_dialog("a\nb\nc", "a\nB\nc\nd", checked=set())

    dialog._on_apply_clicked(object())

    assert dialog.applied is False
    assert applied == []
    assert dialog.dialog.ended_with is None
    assert announcements and "No changes" in announcements[0]


def test_diff_review_accept_all_applies_every_hunk_and_closes() -> None:
    # Accept All must apply (not merely tick the boxes) and end the dialog.
    dialog, applied, announcements = _make_diff_dialog("a\nb\nc", "a\nB\nc\nd", checked=set())

    dialog._on_accept_all_clicked(object())

    assert dialog.applied is True
    assert applied == ["a\nB\nc\nd"]
    assert dialog.dialog.ended_with == 1


def test_diff_review_accept_single_hunk_applies_and_closes() -> None:
    # The single-change Accept path also routes through _on_accept_all_clicked.
    dialog, applied, _ = _make_diff_dialog("a\nb\nc", "a\nB\nc", checked=set())

    dialog._on_accept_all_clicked(object())

    assert dialog.applied is True
    assert applied == ["a\nB\nc"]
    assert dialog.dialog.ended_with == 1


def test_diff_review_reject_dismisses_without_applying() -> None:
    dialog, applied, announcements = _make_diff_dialog("a\nb\nc", "a\nB\nc", checked={0})

    dialog._on_reject_clicked(object())

    assert dialog.applied is False
    assert applied == []
    assert dialog.dialog.ended_with == 0  # ID_CANCEL
    assert announcements and "unchanged" in announcements[0].lower()
