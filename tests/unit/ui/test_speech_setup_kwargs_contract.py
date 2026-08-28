"""The Speech Hub hands SpeechSetupDialog every argument it demands (#1422).

Reported three times against the shipped 0.9.0 build (#1395, #1417, #1422),
each from somebody installing a Kokoro voice:

    TypeError: SpeechSetupDialog.__init__() missing 2 required keyword-only
    arguments: 'kokoro_ok' and 'kokoro_can_install'

The dialog grew two required keyword-only parameters and the frame that builds
its arguments was updated in the same change -- but nothing tied the two
together, so the window between them shipped. A missing keyword-only argument is
a ``TypeError`` at construction, which means the Speech Hub does not open at
all: no dictation, no voices, a crash report.

This is the tie. It reads the dialog's real signature and the dict literals
each builder writes, so adding a required parameter without supplying it fails
here rather than in front of somebody installing a voice.

**Both** builders are checked (2026-08-27). The gate originally read only
``MainFrame`` -- but ``quill/apps/studio.py`` builds the same dicts for Audio
Studio's Speech Hub, so half the surface was unguarded, and a fourth report
of the same TypeError (#1460) arrived while that was true. The dialog now
also defaults the Kokoro pair to the live probes, so an omission degrades to
a correct answer instead of a crash; this gate keeps every *other* required
argument honest for both builders.
"""

from __future__ import annotations

import ast
import inspect
import pathlib

import pytest

#: Supplied at the call site in ``speech_hub_dialog.py`` rather than through the
#: kwargs dicts, so they are not the frame's job to provide.
_AT_THE_CALL_SITE = frozenset({"embed_in", "on_action"})

#: The dict literals in ``MainFrame`` that feed the two SpeechSetupDialog pages.
_KWARG_DICTS = ("common_dict_kwargs", "dictation_offline_kwargs", "dictation_online_kwargs")


def _required_keyword_only() -> set[str]:
    pytest.importorskip("wx")
    from quill.ui.speech_setup_dialog import SpeechSetupDialog

    signature = inspect.signature(SpeechSetupDialog.__init__)
    return {
        name
        for name, parameter in signature.parameters.items()
        if parameter.kind is parameter.KEYWORD_ONLY and parameter.default is parameter.empty
    }


#: Every module that builds the Speech Hub's kwargs. A third one must join this
#: list -- that is the point of the gate.
BUILDERS = ("quill/ui/main_frame.py", "quill/apps/studio.py")


def _keys_supplied_by(builder: str) -> set[str]:
    """Every key *builder* puts into the dicts it hands the Speech Hub.

    Parsed rather than executed: building them for real needs a live frame, a
    speech registry and a machine probe, none of which belong in a unit test --
    and the failure being guarded against is a *static* one, a name that is not
    written down anywhere.
    """
    source = (pathlib.Path(__file__).resolve().parents[3] / builder).read_text(encoding="utf-8")
    keys: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.AnnAssign | ast.Assign):
            continue
        targets = [node.target] if isinstance(node, ast.AnnAssign) else node.targets
        names = {t.id for t in targets if isinstance(t, ast.Name)}
        if not names & set(_KWARG_DICTS):
            continue
        value = node.value
        if not isinstance(value, ast.Dict):
            continue
        for key in value.keys:
            # ``**common_dict_kwargs`` inside another literal appears as a None
            # key; its own keys are collected when that literal is visited.
            if isinstance(key, ast.Constant) and isinstance(key.value, str):
                keys.add(key.value)
    return keys


@pytest.mark.parametrize("builder", BUILDERS)
def test_the_kwargs_dicts_were_found_at_all(builder: str) -> None:
    """A contract test that parsed nothing would pass forever."""
    keys = _keys_supplied_by(builder)

    assert len(keys) > 8, sorted(keys)
    assert "provider" in keys and "machine_summary" in keys


@pytest.mark.parametrize("builder", BUILDERS)
def test_every_required_argument_is_supplied(builder: str) -> None:
    required = _required_keyword_only() - _AT_THE_CALL_SITE
    supplied = _keys_supplied_by(builder)

    missing = sorted(required - supplied)

    assert not missing, (
        f"SpeechSetupDialog requires these keyword-only arguments and {builder} "
        "never puts them in the kwargs it hands the Speech Hub: " + ", ".join(missing)
    )


@pytest.mark.parametrize("builder", BUILDERS)
def test_the_two_kokoro_arguments_are_specifically_covered(builder: str) -> None:
    """The pair four separate crash reports named."""
    supplied = _keys_supplied_by(builder)

    assert "kokoro_ok" in supplied
    assert "kokoro_can_install" in supplied


def test_omitting_the_kokoro_pair_is_no_longer_fatal() -> None:
    """The cure for the class: the dialog answers for itself (#1460).

    Two builders feed this dialog and a third could appear; a required
    argument one of them forgets is a TypeError in front of somebody pressing
    Manage Voices. The parameters keep their place in the signature -- a
    caller with real answers still passes them -- but omitting them now
    resolves to the live probe instead of crashing.
    """
    pytest.importorskip("wx")
    import inspect

    from quill.ui.speech_setup_dialog import SpeechSetupDialog

    signature = inspect.signature(SpeechSetupDialog.__init__)
    for name in ("kokoro_ok", "kokoro_can_install"):
        assert signature.parameters[name].default is None, name

    source = (
        pathlib.Path(__file__).resolve().parents[3] / "quill" / "ui" / "speech_setup_dialog.py"
    ).read_text(encoding="utf-8")
    assert "is_kokoro_onnx_available()" in source
    assert "kokoro_onnx_install_supported()" in source
