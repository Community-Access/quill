"""GATE-HELPREF: docs/f1-help-reference.md is generated, never hand-written.

The document renders every app's authored F1 content -- window purposes and
control help sentences -- from the same sources the apps read at runtime.
The only way for it to lie is to skip regeneration; this closes that.
"""

from __future__ import annotations

from quill.tools import build_help_reference


def test_the_committed_reference_matches_the_authored_help() -> None:
    committed = (
        build_help_reference.OUTPUT_PATH.read_text(encoding="utf-8")
        if build_help_reference.OUTPUT_PATH.exists()
        else ""
    )
    assert committed == build_help_reference.generate(), (
        "docs/f1-help-reference.md has drifted from the surface_help "
        "catalogues / SetHelpText calls. Regenerate with: "
        "python -m quill.tools.build_help_reference --write"
    )


def test_every_configured_app_appears() -> None:
    text = build_help_reference.OUTPUT_PATH.read_text(encoding="utf-8")
    for config in build_help_reference.APPS:
        assert f"## {config.display}" in text, (
            f"{config.display} missing from the F1 help reference -- its "
            "catalogue failed to import or was renamed"
        )


def test_the_extraction_actually_extracts() -> None:
    """A broken SetHelpText scan would render an empty (passing) document."""
    text = build_help_reference.generate()
    assert text.count("### Every authored control help sentence") >= 6
    assert text.count("**") > 50, "window purposes missing"


#: Which audit gates each published app. The reference and the audit must scan
#: the same modules: when they did not, the Release Channel, Tutorials and
#: Converter dialog sentences were gated but never published (2026-10-04).
_AUDITS = {
    "Quill Radio": "radio",
    "QUILL Cast": "cast",
    "QUILL Media Player": "player",
    "QUILL Audio Studio": "studio",
    "Quill Inkwell": "inkwell",
    "Quill Weather": "weather",
    "Quill Converter": "converter",
    "Quill Beacon": "beacon",
    "QUILL Lite": "lite",
}


def test_the_reference_scans_what_each_audit_scans() -> None:
    import importlib

    assert {config.display for config in build_help_reference.APPS} == set(_AUDITS)
    for config in build_help_reference.APPS:
        audit = importlib.import_module(f"quill.tools.{_AUDITS[config.display]}_help_audit")
        assert config.scan_dirs == tuple(audit._SCAN_DIRS), config.display
        assert config.scan_globs == tuple(audit._SCAN_GLOBS), (
            f"{config.display}: build_help_reference.APPS scans {config.scan_globs}, "
            f"its audit scans {tuple(audit._SCAN_GLOBS)}. Keep them in step, or a "
            "gated sentence is never published (or a published one never gated)."
        )
