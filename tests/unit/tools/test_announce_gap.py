"""Tests for the announce-gap gate (GATE-12)."""

from __future__ import annotations

from pathlib import Path


def test_announce_gap_gate_passes_on_repo() -> None:
    """GATE-12: no dialog file has a status StaticText updated without announce."""
    from quill.tools.check_announce_gap import check_announce_gap

    violations = check_announce_gap()
    assert violations == [], (
        "GATE-12 announce-gap violations found. Each dialog that updates a "
        "status StaticText via SetLabel must also announce via _announce() or "
        "announce_cb. Add the announce_cb parameter and _set_status() helper "
        "(see ai_chat_dialog.py), or add the file to the allowlist if the "
        "SetLabel usage is not a user-facing status message.\n\n" + "\n".join(violations)
    )


def test_announce_gap_gate_detects_violation(tmp_path: Path) -> None:
    """GATE-12 correctly flags a file with a silent status update."""
    from quill.tools.check_announce_gap import check_announce_gap

    bad_file = tmp_path / "quill" / "ui" / "bad_dialog.py"
    bad_file.parent.mkdir(parents=True)
    bad_file.write_text(
        "class BadDialog:\n"
        "    def __init__(self):\n"
        "        self._status_label = wx.StaticText(panel, label='')\n"
        "    def _set_status(self, msg):\n"
        "        self._status_label.SetLabel(msg)\n",
        encoding="utf-8",
    )
    violations = check_announce_gap(tmp_path)
    assert any("bad_dialog.py" in v for v in violations), (
        f"Gate should have flagged bad_dialog.py but found no violations: {violations}"
    )


def test_announce_gap_gate_passes_with_announce(tmp_path: Path) -> None:
    """GATE-12 does not flag a file that announces."""
    from quill.tools.check_announce_gap import check_announce_gap

    good_file = tmp_path / "quill" / "ui" / "good_dialog.py"
    good_file.parent.mkdir(parents=True)
    good_file.write_text(
        "class GoodDialog:\n"
        "    def __init__(self, announce_cb=None):\n"
        "        self._status_label = wx.StaticText(panel, label='')\n"
        "        self._announce = announce_cb or (lambda _: None)\n"
        "    def _set_status(self, msg):\n"
        "        self._status_label.SetLabel(msg)\n"
        "        self._announce(msg)\n",
        encoding="utf-8",
    )
    violations = check_announce_gap(tmp_path)
    assert violations == [], f"Should have been clean: {violations}"
