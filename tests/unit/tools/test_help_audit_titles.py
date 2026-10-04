"""The shared help-audit engine sees every way a window gets its title.

Until 2026-10-04 the title check saw only ``wx.Dialog(title=...)`` and
``wx.Frame(title=...)`` calls. A window written as a *subclass* -- every
release-channel window, the dictation settings, the hosted-AI conversation --
passes its title to ``super().__init__`` and was never checked, so several
shipped answering F1 with the generic paragraph. Two smaller blind spots went
with it: a translated literal (``_("Tag Editor")``) was "unresolvable", and an
f-string prefix such as ``"Trail -- "`` was compared without the text that
always follows it.
"""

from __future__ import annotations

import ast
import textwrap

from quill.tools.help_audit import _HelpVisitor


def _titles(source: str) -> list[str | None]:
    tree = ast.parse(textwrap.dedent(source))
    visitor = _HelpVisitor("m.py", tree)
    visitor.visit(tree)
    return [title for _key, _line, title in visitor.titles]


def test_a_dialog_subclass_title_is_checked() -> None:
    assert _titles(
        """
        class Settings(wx.Dialog):
            def __init__(self, parent):
                super().__init__(parent, title="Dictation Settings")
        """
    ) == ["Dictation Settings"]


def test_super_init_outside_a_window_class_is_not_a_title() -> None:
    assert (
        _titles(
            """
            class Helper(Base):
                def __init__(self):
                    super().__init__(title="not a window")
            """
        )
        == []
    )


def test_translated_literals_resolve() -> None:
    assert _titles('wx.Dialog(None, title=str(_("Tag Editor")))') == ["Tag Editor"]


def test_an_fstring_prefix_keeps_what_follows_it() -> None:
    (title,) = _titles('wx.Dialog(None, title=f"Trail -- {name}")')
    assert title is not None
    assert title.startswith("Trail -- ") and title.strip() != "Trail --"
