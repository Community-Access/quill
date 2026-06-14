from __future__ import annotations

import ast
from pathlib import Path

from quill.tools.check_banned_patterns import (
    _REPO_ROOT,
    _BareWxVisitor,
    _check_checklistbox,
    _check_dead_region_attrs,
    _check_dialog_contract,
    _check_dialog_registry,
    _check_raw_xml,
    _check_threading_thread,
    _check_wx_message_box,
    find_violations,
)


def _bare_wx_violations(source: str) -> list[tuple[int, str]]:
    visitor = _BareWxVisitor()
    visitor.visit(ast.parse(source))
    return visitor.violations


def test_clean_tree_has_no_violations() -> None:
    assert find_violations() == []


def test_bare_wx_without_local_binding_is_flagged() -> None:
    # The BUG-2 class: wx is never imported at module scope, so this is a
    # NameError at runtime.
    source = "class Frame:\n    def do(self):\n        return wx.GetTextFromUser('x')\n"
    violations = _bare_wx_violations(source)
    assert len(violations) == 1
    assert "bare 'wx.'" in violations[0][1]


def test_wx_bound_to_self_attr_is_allowed() -> None:
    source = (
        "class Frame:\n"
        "    def do(self):\n"
        "        wx = self._wx\n"
        "        return wx.GetTextFromUser('x')\n"
    )
    assert _bare_wx_violations(source) == []


def test_wx_from_enclosing_scope_in_nested_function_is_allowed() -> None:
    source = (
        "class Frame:\n"
        "    def do(self):\n"
        "        wx = self._wx\n"
        "        def cb():\n"
        "            return wx.CallAfter(lambda: None)\n"
        "        return cb\n"
    )
    assert _bare_wx_violations(source) == []


def test_wx_as_parameter_is_allowed() -> None:
    source = "def helper(wx):\n    return wx.ID_OK\n"
    assert _bare_wx_violations(source) == []


def test_raw_et_fromstring_outside_safe_xml_is_flagged(tmp_path: Path) -> None:
    module = tmp_path / "reader.py"
    module.write_text(
        "import xml.etree.ElementTree as ET\n\n\n"
        "def parse(text):\n    return ET.fromstring(text)\n",
        encoding="utf-8",
    )
    violations = _check_raw_xml([module])
    assert len(violations) == 1
    assert "safe_xml" in violations[0].message


def test_safe_xml_fromstring_call_is_not_flagged(tmp_path: Path) -> None:
    module = tmp_path / "reader.py"
    module.write_text(
        "from quill.core.safe_xml import fromstring\n\n\n"
        "def parse(text):\n    return fromstring(text)\n",
        encoding="utf-8",
    )
    assert _check_raw_xml([module]) == []


def test_dialog_align_right_is_flagged(tmp_path: Path) -> None:
    # The A11Y-4 bug class: button sizers added with wx.ALIGN_RIGHT pushed
    # OK/Cancel off-screen and broke focus order.
    module = tmp_path / "panel.py"
    module.write_text(
        "def build(self):\n"
        "    dialog = wx.Dialog(self)\n"
        "    root.Add(buttons, 0, wx.ALL | wx.ALIGN_RIGHT, 8)\n"
        "    dialog.Destroy()\n",
        encoding="utf-8",
    )
    violations = _check_dialog_contract([module])
    assert any("ALIGN_RIGHT" in v.message for v in violations)


def test_dialog_expand_button_sizer_is_allowed(tmp_path: Path) -> None:
    module = tmp_path / "panel.py"
    module.write_text(
        "def build(self):\n"
        "    dialog = wx.Dialog(self)\n"
        "    buttons.AddStretchSpacer(1)\n"
        "    root.Add(buttons, 0, wx.ALL | wx.EXPAND, 8)\n"
        "    dialog.Destroy()\n",
        encoding="utf-8",
    )
    assert _check_dialog_contract([module]) == []


def test_raw_dialog_without_destroy_is_flagged(tmp_path: Path) -> None:
    # The crash-recovery leak class: a modal dialog built but never destroyed.
    module = tmp_path / "panel.py"
    module.write_text(
        "def build(self):\n    dialog = wx.Dialog(self)\n    dialog.ShowModal()\n",
        encoding="utf-8",
    )
    violations = _check_dialog_contract([module])
    assert any("Destroy" in v.message for v in violations)


def test_with_dialog_form_is_exempt_from_destroy(tmp_path: Path) -> None:
    # The auto-destroying context-manager form needs no explicit Destroy().
    module = tmp_path / "panel.py"
    module.write_text(
        "def build(self):\n    with wx.Dialog(self) as dialog:\n        dialog.ShowModal()\n",
        encoding="utf-8",
    )
    assert _check_dialog_contract([module]) == []


def test_dialog_registry_cross_check_is_clean() -> None:
    # Every dialog surface in source is registered and classified in the
    # committed snapshot; the live tree must have zero registry violations.
    assert _check_dialog_registry() == []


def test_checklistbox_is_flagged(tmp_path: Path) -> None:
    # A11Y-SR-1: wx.CheckListBox does not announce checked state to screen
    # readers on navigation; new uses must be caught at commit time.
    module = tmp_path / "dlg.py"
    module.write_text(
        "def build(panel):\n    chooser = wx.CheckListBox(panel, choices=['a', 'b'])\n",
        encoding="utf-8",
    )
    violations = _check_checklistbox([module])
    assert len(violations) == 1
    assert "A11Y-SR-1" in violations[0].message


def test_checklistbox_ok_comment_exempts(tmp_path: Path) -> None:
    # A known call site with an explanatory comment is allowed through.
    module = tmp_path / "dlg.py"
    module.write_text(
        "def build(panel):\n"
        "    chooser = wx.CheckListBox(  # A11Y-SR-1-OK: state in label\n"
        "        panel, choices=['a'])\n",
        encoding="utf-8",
    )
    assert _check_checklistbox([module]) == []


def test_threading_thread_is_flagged(tmp_path: Path) -> None:
    # #40: direct threading.Thread in quill/ui bypasses QuillTaskManager.
    module = tmp_path / "worker.py"
    module.write_text(
        "import threading\n\n\n"
        "def go():\n    threading.Thread(target=lambda: None, daemon=True).start()\n",
        encoding="utf-8",
    )
    violations = _check_threading_thread([module])
    assert len(violations) == 1
    assert "GATE-40" in violations[0].message


def test_threading_thread_ok_marker_exempts(tmp_path: Path) -> None:
    module = tmp_path / "worker.py"
    module.write_text(
        "import threading\n\n\n"
        "def go():\n"
        "    threading.Thread(  # GATE-40-OK: legacy short-lived worker\n"
        "        target=lambda: None, daemon=True\n"
        "    ).start()\n",
        encoding="utf-8",
    )
    assert _check_threading_thread([module]) == []


def test_wx_message_box_is_flagged(tmp_path: Path) -> None:
    # #41: raw wx.MessageBox bypasses the announce-dialog wrapper.  The
    # source path must live under quill/ui or quill/devtools (the governed
    # directories) for the gate to apply, so we drop a fixture file in the
    # real source tree and assert the gate flags it, then clean up.

    target_dir = _REPO_ROOT / "quill" / "ui" / "_gate41_fixture"
    target_dir.mkdir(exist_ok=True, parents=True)
    module = target_dir / "dlg.py"
    module.write_text(
        "import wx\n\n\ndef go():\n    wx.MessageBox('oops', 'Err', wx.OK | wx.ICON_ERROR)\n",
        encoding="utf-8",
    )
    try:
        violations = _check_wx_message_box([module])
        assert len(violations) == 1
        assert "GATE-41" in violations[0].message
    finally:
        module.unlink()
        target_dir.rmdir()


def test_wx_message_box_ok_marker_exempts(tmp_path: Path) -> None:
    target_dir = _REPO_ROOT / "quill" / "ui" / "_gate41_fixture"
    target_dir.mkdir(exist_ok=True, parents=True)
    module = target_dir / "dlg.py"
    module.write_text(
        "import wx\n\n\n"
        "def go():\n"
        "    wx.MessageBox(  # GATE-41-OK: tests, no UI to announce through\n"
        "        'oops', 'Err', wx.OK\n"
        "    )\n",
        encoding="utf-8",
    )
    try:
        assert _check_wx_message_box([module]) == []
    finally:
        module.unlink()
        target_dir.rmdir()


def test_dead_region_attrs_enter_is_flagged(tmp_path: Path) -> None:
    # BUG-REGION / #165: self._enter_region does not exist on MainFrame.
    module = tmp_path / "mixin.py"
    module.write_text(
        "def show(self):\n    self._enter_region('dialog')\n",
        encoding="utf-8",
    )
    violations = _check_dead_region_attrs([module])
    assert len(violations) == 1
    assert "BUG-REGION" in violations[0].message
    assert "_region_tracker" in violations[0].message


def test_dead_region_attrs_exit_is_flagged(tmp_path: Path) -> None:
    module = tmp_path / "mixin.py"
    module.write_text(
        "def hide(self):\n    self._exit_region('dialog')\n",
        encoding="utf-8",
    )
    violations = _check_dead_region_attrs([module])
    assert len(violations) == 1
    assert "BUG-REGION" in violations[0].message


def test_dead_region_attrs_correct_form_is_clean(tmp_path: Path) -> None:
    module = tmp_path / "mixin.py"
    module.write_text(
        "def show(self):\n"
        "    self._region_tracker.enter('dialog')\n"
        "    self._region_tracker.exit('dialog')\n",
        encoding="utf-8",
    )
    assert _check_dead_region_attrs([module]) == []
