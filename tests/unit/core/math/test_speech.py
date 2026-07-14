"""The best-available reading of an equation: real MathCAT, or the template fallback."""

from __future__ import annotations

import pytest

from quill.core.math import speech
from quill.core.math.navigator import EquationNavigator, parse_equation

pytest.importorskip("latex2mathml")


def test_falls_back_to_template_when_mathcat_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(speech, "mathcat_available", lambda: False)
    root = parse_equation("a^2 + b^2 = c^2")
    nav = EquationNavigator(root)
    assert speech.speak(nav.current) == "a squared plus b squared equals c squared"


def test_falls_back_to_template_when_mathcat_engine_import_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """speech.speak must never raise, even if quill.core.math.mathcat_engine is broken."""
    import sys

    monkeypatch.setitem(sys.modules, "quill.core.math.mathcat_engine", None)
    root = parse_equation("x")
    nav = EquationNavigator(root)
    assert speech.speak(nav.current) == "x"


def test_mathcat_available_false_without_engine_pack() -> None:
    # In this test environment the engine pack is not installed at the real
    # app-data location, so this exercises the real (not monkeypatched) path.
    from quill.core.math import mathcat_engine

    if not mathcat_engine.is_available():
        assert speech.mathcat_available() is False


def test_real_mathcat_used_when_installed() -> None:
    from quill.core.math import mathcat_engine

    if not mathcat_engine.is_available():
        pytest.skip("MathCAT engine pack not installed")
    root = parse_equation("a^2 + b^2 = c^2")
    nav = EquationNavigator(root)
    result = speech.speak(nav.current)
    assert "squared" in result
    # Confirms the real engine (not the template fallback) actually produced
    # this: MathCAT phrases the equals sign differently than the template.
    assert result != "a squared plus b squared equals c squared"
