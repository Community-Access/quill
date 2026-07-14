"""Startup crash-guard tests.

These tests prevent a class of regression where app startup crashes silently
because:

1. A mixin ``_init_*`` method calls ``self.Bind(...)`` directly, which fails on
   MainFrame because it is a plain Python class (not a wx.Frame subclass).
   MainFrame wraps ``self.frame = wx.Frame(...)``; bindings must go through
   ``self.frame.Bind(...)`` or the ``_help_frame`` property.

2. A mixin init method is invoked before ``self.frame`` is created in
   ``MainFrame.__init__``.

The bug caught by this suite (fixed 2026-06-12): ``ContextHelpMixin._init_context_help``
called ``self.Bind(wx.EVT_CHILD_FOCUS, ...)`` and used ``ContextHelpDialog(self, ...)``
before ``self.frame`` existed, crashing QUILL at startup with:

    AttributeError: 'MainFrame' object has no attribute 'Bind'

These are structural source-analysis tests — they parse the source rather than
running the app, so they work in CI without a display.
"""

from __future__ import annotations

import re
from pathlib import Path

_UI = Path(__file__).resolve().parents[3] / "quill" / "ui"
_MAIN_FRAME = _UI / "main_frame.py"
_CONTEXT_HELP = _UI / "context_help.py"


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Rule 1: context_help.py must never call self.Bind() — only _help_frame.Bind()


def test_context_help_mixin_uses_help_frame_not_self_bind():
    """ContextHelpMixin must never call self.Bind(); must use self._help_frame.Bind()."""
    source = _source(_CONTEXT_HELP)
    # Look for self.Bind( — any direct call on self, not on _help_frame
    direct_binds = re.findall(r"(?<!\._help_frame)(?<!frame)(?<!self\.frame)\bself\.Bind\(", source)
    assert not direct_binds, (
        "context_help.py must not call self.Bind() directly — "
        "MainFrame is not a wx.Frame subclass. Use self._help_frame.Bind()."
    )


def test_context_help_mixin_defines_help_frame_property():
    """ContextHelpMixin must define _help_frame so subclasses can override it."""
    source = _source(_CONTEXT_HELP)
    assert "_help_frame" in source, (
        "context_help.py must define a _help_frame property for wx.Window delegation."
    )


# ---------------------------------------------------------------------------
# Rule 2: _init_context_help must be called AFTER self.frame is created


def test_init_context_help_called_after_frame_creation():
    """_init_context_help() must follow self.frame = wx.Frame(...) in __init__."""
    source = _source(_MAIN_FRAME)
    frame_pos = source.find("self.frame = wx.Frame(None")
    init_pos = source.find("_init_context_help()")
    assert frame_pos != -1, "Could not find self.frame = wx.Frame(None in main_frame.py"
    assert init_pos != -1, "Could not find _init_context_help() call in main_frame.py"
    assert frame_pos < init_pos, (
        "_init_context_help() must be called AFTER self.frame = wx.Frame(None...) — "
        "calling it before means self.frame doesn't exist when the mixin tries to bind."
    )


# ---------------------------------------------------------------------------
# Rule 3: wx-dependent mixin init calls must not precede self.frame creation
#
# Only check the specific methods that are known to require self.frame.
# Not all _init_* calls need self.frame (e.g. _init_abbreviations is safe early).

_REQUIRES_FRAME = [
    "_init_context_help()",
    "_init_context_menu()",
]


def test_frame_dependent_mixin_inits_called_after_frame_creation():
    """Mixin init methods that use self.frame must come after self.frame = wx.Frame."""
    source = _source(_MAIN_FRAME)
    frame_pos = source.find("self.frame = wx.Frame(None")
    assert frame_pos != -1, "Could not find self.frame = wx.Frame(None in main_frame.py"

    for call in _REQUIRES_FRAME:
        pos = source.find(call)
        if pos == -1:
            continue  # not present — nothing to check
        assert pos > frame_pos, (
            f"{call} appears BEFORE self.frame is created in main_frame.py. "
            "This crashes at startup with AttributeError because MainFrame is "
            "not a wx.Frame subclass — it wraps self.frame."
        )


# ---------------------------------------------------------------------------
# Rule 4: MainFrame must not inherit from wx.Frame (it wraps it)


def test_main_frame_is_not_wx_frame_subclass():
    """MainFrame uses composition (self.frame = wx.Frame(...)), not inheritance.

    Calling self.Bind() on MainFrame doesn't work. This test pins that
    invariant: if someone accidentally adds wx.Frame to the MRO, bindings
    may appear to work in some contexts but fail in others.
    """
    source = _source(_MAIN_FRAME)
    # Look for 'class MainFrame(' definition line
    class_match = re.search(r"^class MainFrame\(([^)]+)\)", source, re.MULTILINE)
    assert class_match, "Could not find MainFrame class definition"
    bases = class_match.group(1)
    assert "wx.Frame" not in bases, (
        "MainFrame must not inherit from wx.Frame — it uses composition "
        "(self.frame = wx.Frame(...)). Binding goes through self.frame.Bind()."
    )


# ---------------------------------------------------------------------------
# Rule 5: Every mixin added to MainFrame MRO that defines _bind_*_menu must
# also be included in the menu contract test source scan


def test_mixin_bind_methods_covered_by_menu_contract_test():
    """All files that define _bind_*_menu() must be included in _menu_source()."""
    contract_source = (Path(__file__).parent / "test_main_frame_menu_contract.py").read_text(
        encoding="utf-8"
    )

    # Find all UI files that define a _bind_*_menu method
    for py_file in _UI.glob("main_frame_*.py"):
        content = py_file.read_text(encoding="utf-8")
        if "_bind_" in content and "_menu" in content:
            if re.search(r"def _bind_\w+_menu\(", content):
                fname = py_file.name
                assert fname in contract_source, (
                    f"{fname} defines a _bind_*_menu method but is not included "
                    "in test_main_frame_menu_contract.py's _menu_source(). "
                    "Add it so new menu IDs are checked for bindings."
                )


# ---------------------------------------------------------------------------
# Rule 6: ContextHelpMixin._help_frame property must be overridden in MainFrame


def test_main_frame_overrides_help_frame_property():
    """MainFrame must override _help_frame to return self.frame."""
    source = _source(_MAIN_FRAME)
    # Must have a _help_frame property returning self.frame
    assert "_help_frame" in source, (
        "MainFrame must override the _help_frame property from ContextHelpMixin "
        "to return self.frame (the actual wx.Window)."
    )
    # Verify it returns self.frame not self
    prop_match = re.search(
        r"def _help_frame.*?return\s+(self\.frame|self)",
        source,
        re.DOTALL,
    )
    assert prop_match, "Could not find _help_frame property definition in main_frame.py"
    assert prop_match.group(1) == "self.frame", (
        "MainFrame._help_frame must return self.frame, not self — "
        "returning self would cause self.Bind() to fail since MainFrame "
        "is not a wx.Frame subclass."
    )


# ---------------------------------------------------------------------------
# Regression: _bind_events() runs during __init__ before the editor exists on
# the first-run/wizard-pending path. _apply_soft_wrap must no-op rather than
# crash with AttributeError: 'MainFrame' object has no attribute 'editor'.


def test_apply_soft_wrap_no_ops_before_editor_exists() -> None:
    from quill.ui.main_frame import MainFrame

    class _Stub:
        pass

    stub = _Stub()
    # No `editor` attribute yet — must return cleanly (it guards before using _wx).
    MainFrame._apply_soft_wrap(stub, True)
    MainFrame._apply_soft_wrap(stub, False)
