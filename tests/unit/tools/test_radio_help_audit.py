"""GATE-RADIO-HELP: F1 help ships with every radio surface and control.

Three enforced facts:

1. **Every window title resolves to a purpose.** A new ``wx.Frame`` /
   ``wx.Dialog`` in the radio UI whose title has no entry in
   ``surface_help`` fails here, so a window cannot ship without saying what
   it is for.
2. **Every helpable control is accounted for.** The committed inventory
   classifies every construction site (``helped`` when the site authors
   ``SetHelpText``, ``named-help`` when its accessible name already carries
   the teaching sentence F1 composes with a role line, ``help-elsewhere`` /
   ``opt-out`` as reviewed exceptions). A brand-new site is ``missing`` until
   a human either authors help or classifies it -- and ``missing`` fails.
3. **The wiring cannot silently disappear.** The dialog contract binds F1 on
   both of its show paths, and Quill Radio registers the handler at startup.
"""

from __future__ import annotations

from pathlib import Path

from quill.tools import radio_help_audit

REPO = Path(__file__).resolve().parents[3]


def test_every_radio_window_title_has_an_authored_purpose() -> None:
    _sites, violations = radio_help_audit.scan()
    assert violations == [], "\n".join(
        f"{v.key}:{v.line}: {v.title!r} -- {v.reason}" for v in violations
    )


def test_control_inventory_matches_source_with_nothing_missing() -> None:
    sites, _violations = radio_help_audit.scan()
    committed = radio_help_audit.load_snapshot()
    live = radio_help_audit.build_snapshot(sites, committed)
    assert live == committed, (
        "Helpable-control sites changed. Run "
        "'python -m quill.tools.radio_help_audit --write', then author "
        "SetHelpText for each new site (or classify it deliberately) -- a "
        "control without help is a question F1 cannot answer."
    )
    missing = sorted(key for key, status in committed.items() if status == "missing")
    assert missing == [], (
        "These controls have no help and no reviewed classification: " + ", ".join(missing)
    )
    assert set(committed.values()) <= radio_help_audit.STATUSES


def test_the_f1_wiring_is_in_place() -> None:
    contract = (REPO / "quill" / "ui" / "dialog_contract.py").read_text(encoding="utf-8")
    assert contract.count("_install_context_help(") >= 3, "both show paths must install the F1 hook"
    radio_app = (REPO / "quill" / "apps" / "radio.py").read_text(encoding="utf-8")
    assert "context_help.activate()" in radio_app
    engine = (REPO / "quill" / "ui" / "app_context_help.py").read_text(encoding="utf-8")
    assert "set_context_help_handler(show_help)" in engine
    shim = (REPO / "quill" / "ui" / "radio" / "context_help.py").read_text(encoding="utf-8")
    assert "app_context_help.activate(surface_help.purpose_for_title)" in shim
