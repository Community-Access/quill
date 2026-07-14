"""The best available spoken reading of an equation.

Tries the real MathCAT engine first (natural, screen-reader-grade output);
falls back to :mod:`quill.core.math.navigator`'s template-based reading when
MathCAT is not installed or fails on the given input. :func:`speak` never
raises — a caller always gets a usable string.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

from quill.core.math.mathml import MATHML_NS
from quill.core.math.navigator import read_aloud as _template_read_aloud


def mathcat_available() -> bool:
    """Return True when the real MathCAT speech engine is installed."""
    try:
        from quill.core.math import mathcat_engine
    except Exception:  # noqa: BLE001 - treat any import problem as "not installed"
        return False
    return mathcat_engine.is_available()


def speak(element: ET.Element) -> str:
    """The best available plain-language reading of *element*.

    *element* should be a node from :class:`quill.core.math.navigator.EquationNavigator`
    (already unwrapped of the ``<math>``/``<semantics>`` unwrapper), not the raw parsed root.
    """
    if mathcat_available():
        try:
            from quill.core.math import mathcat_engine

            mathml = f'<math xmlns="{MATHML_NS}">{ET.tostring(element, encoding="unicode")}</math>'
            return mathcat_engine.mathml_to_speech(mathml)
        except Exception:  # noqa: BLE001 - any MathCAT failure falls back, never surfaces
            pass
    return _template_read_aloud(element)
