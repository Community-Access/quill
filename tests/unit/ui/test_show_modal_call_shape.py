"""Every hand-off of ``_show_modal_dialog`` is called with its label.

``MainFrame._show_modal_dialog(dialog, label)`` requires the label -- it is
what the dialog contract announces -- and a dialog module that receives the
bound method under a shorter name (``self._show_modal``) has no signature in
front of it when it calls. Two modules called it with one argument, and the
result was a TypeError **when the user pressed the button**, not at startup:
crash report #1442 (the Copilot Set Up flow), plus its unreported twin in the
agent validator, found while fixing it.

Source-level, because that is where the drift happens: the pattern
``._show_modal(self.dialog)`` with nothing after the argument is exactly the
call that compiles fine and crashes live.
"""

from __future__ import annotations

import re
from pathlib import Path

_UI = Path(__file__).resolve().parents[3] / "quill" / "ui"

#: A one-argument call of a stored show-modal callable. The comma test is the
#: point: ``_show_modal(self.dialog, "Label")`` does not match.
_ONE_ARG_CALL = re.compile(r"\._show_modal\(\s*self\.(?:_)?dialog\s*\)")


def test_no_show_modal_call_omits_the_label() -> None:
    offenders = []
    for path in _UI.rglob("*.py"):
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in _ONE_ARG_CALL.finditer(text):
            line = text[: match.start()].count("\n") + 1
            offenders.append(f"{path.relative_to(_UI.parent.parent)}:{line}")
    assert not offenders, (
        "_show_modal called without its label (the #1442 crash shape):\n  " + "\n  ".join(offenders)
    )


def test_the_two_fixed_sites_pass_real_labels() -> None:
    copilot = (_UI / "copilot_onboarding_dialog.py").read_text(encoding="utf-8")
    validator = (_UI / "agent_validator_dialog.py").read_text(encoding="utf-8")
    assert '_show_modal(self.dialog, "Set Up GitHub Copilot")' in copilot
    assert '_show_modal(self.dialog, "Validate Agents")' in validator
