"""The Speech Hub's dialogs must be constructible from the kwargs it passes (#1364).

``SpeechSetupDialog`` gained two required keyword-only parameters; the Speech
Hub's call site did not pass them for two and a half weeks. Anyone on a build
cut inside that window crashed the moment the Dictation (Offline) tab was
constructed -- which is on hub open, so the whole Speech Hub was unreachable.

Nothing caught it: the kwargs travel as ``**dictation_offline_kwargs``, a dict
built twelve thousand lines away in ``main_frame.py``, and ``quill/ui`` is
excluded from mypy. This test is the cheap thing that does catch it -- it reads
the keys the hub actually passes out of the source (following ``**spread``) and
checks them against the real constructor signatures.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest

from quill.ui.speech_setup_dialog import SpeechSetupDialog
from quill.ui.voice_browser_dialog import VoiceBrowserDialog

_MAIN_FRAME = Path(str(inspect.getsourcefile(SpeechSetupDialog))).with_name("main_frame.py")
_TREE = ast.parse(_MAIN_FRAME.read_text(encoding="utf-8"))

#: Supplied by SpeechHubDialog itself when it constructs each tab, not by the
#: kwargs dict, so they are never "missing" from the call site.
_SUPPLIED_BY_HUB = {"parent", "embed_in", "on_action"}


def _dict_literals() -> dict[str, ast.Dict]:
    found: dict[str, ast.Dict] = {}
    for node in ast.walk(_TREE):
        target: ast.expr | None = None
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Dict):
            target = node.targets[0]
        elif isinstance(node, ast.AnnAssign) and isinstance(node.value, ast.Dict):
            target = node.target
        if isinstance(target, ast.Name) and isinstance(node.value, ast.Dict):
            found.setdefault(target.id, node.value)
    return found


def _keys(name: str, seen: frozenset[str] = frozenset()) -> set[str]:
    """Every keyword ``name`` carries, following ``**other`` spreads."""
    literals = _dict_literals()
    literal = literals.get(name)
    assert literal is not None, f"{name} = {{...}} not found in main_frame.py"
    keys: set[str] = set()
    for key, value in zip(literal.keys, literal.values, strict=True):
        if key is None:  # a **spread
            if isinstance(value, ast.Name) and value.id not in seen:
                keys |= _keys(value.id, seen | {name})
        elif isinstance(key, ast.Constant) and isinstance(key.value, str):
            keys.add(key.value)
    return keys


def _required_keyword_only(cls: type) -> set[str]:
    return {
        name
        for name, parameter in inspect.signature(cls.__init__).parameters.items()
        if parameter.kind is inspect.Parameter.KEYWORD_ONLY
        and parameter.default is inspect.Parameter.empty
    }


def _accepted(cls: type) -> set[str] | None:
    """Every keyword the constructor accepts, or None when it takes ``**kwargs``."""
    signature = inspect.signature(cls.__init__)
    if any(p.kind is inspect.Parameter.VAR_KEYWORD for p in signature.parameters.values()):
        return None
    return {
        name
        for name, parameter in signature.parameters.items()
        if parameter.kind
        in (inspect.Parameter.KEYWORD_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
        and name != "self"
    }


_CASES = [
    ("dictation_offline_kwargs", SpeechSetupDialog),
    ("read_aloud_offline_kwargs", VoiceBrowserDialog),
]


@pytest.mark.parametrize(("kwargs_name", "dialog"), _CASES)
def test_hub_passes_every_required_parameter(kwargs_name: str, dialog: type) -> None:
    missing = _required_keyword_only(dialog) - _keys(kwargs_name) - _SUPPLIED_BY_HUB
    assert not missing, (
        f"{dialog.__name__} requires {sorted(missing)}, which {kwargs_name} does "
        "not pass. The Speech Hub raises TypeError the moment that tab is built, "
        "so the whole hub is unreachable (#1364). Add the key at the call site, "
        "or give the parameter a default."
    )


@pytest.mark.parametrize(("kwargs_name", "dialog"), _CASES)
def test_hub_passes_nothing_the_dialog_would_reject(kwargs_name: str, dialog: type) -> None:
    accepted = _accepted(dialog)
    if accepted is None:
        pytest.skip(f"{dialog.__name__} accepts **kwargs")
    unexpected = _keys(kwargs_name) - accepted
    assert not unexpected, (
        f"{dialog.__name__} would reject {sorted(unexpected)} passed by "
        f"{kwargs_name} -- the mirror image of #1364."
    )
