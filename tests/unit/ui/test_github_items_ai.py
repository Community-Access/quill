"""AI thread summaries always retain a source link and omission note."""

from __future__ import annotations

from types import SimpleNamespace

from quill.ui.github_items_dialog_ai import GitHubItemsAiMixin


def test_summary_presents_its_github_source_and_truncation_status() -> None:
    class _Details:
        value = "Existing item details"

        def GetValue(self) -> str:
            return self.value

        def SetValue(self, value: str) -> None:
            self.value = value

        def SetFocus(self) -> None:
            pass

        def SetInsertionPoint(self, _index: int) -> None:
            pass

    announcements: list[str] = []
    dialog = SimpleNamespace(_details=_Details(), _announce=announcements.append)

    GitHubItemsAiMixin._on_summary_ready(
        dialog,
        42,
        "The issue is waiting on a test fix.",
        "https://github.com/owner/repo/issues/42",
        True,
    )

    assert "The issue is waiting on a test fix." in dialog._details.value
    assert "https://github.com/owner/repo/issues/42" in dialog._details.value
    assert "middle of the discussion was omitted" in dialog._details.value
