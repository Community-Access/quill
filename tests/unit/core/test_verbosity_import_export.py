"""Tests for verbosity profile import / export (§30)."""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.verbosity import import_export
from quill.core.verbosity.channels import Channel
from quill.core.verbosity.import_export import (
    PROFILE_IO_FORMAT,
    ProfileImportError,
    export_profile,
    from_json,
    import_profile,
    to_json,
)
from quill.core.verbosity.profiles import CustomProfile


def _profile() -> CustomProfile:
    return CustomProfile(
        name="Jeff quiet meeting",
        base="Quiet",
        channels=Channel.BRAILLE | Channel.VISUAL,
        per_verb_overrides={"nav.next_line": "L{line}"},
        templates={"Concise": "{line}"},
    )


def test_export_envelope_shape() -> None:
    data = export_profile(_profile())
    assert data["format"] == PROFILE_IO_FORMAT
    assert data["profile"]["name"] == "Jeff quiet meeting"


def test_round_trip_through_json() -> None:
    restored = from_json(to_json(_profile()))
    assert restored == _profile()


def test_import_rejects_non_object() -> None:
    with pytest.raises(ProfileImportError):
        import_profile(["not", "an", "object"])


def test_import_rejects_wrong_format() -> None:
    with pytest.raises(ProfileImportError):
        import_profile({"format": "something-else", "profile": {"name": "x"}})


def test_import_rejects_missing_profile() -> None:
    with pytest.raises(ProfileImportError):
        import_profile({"format": PROFILE_IO_FORMAT})


def test_import_rejects_blank_name() -> None:
    with pytest.raises(ProfileImportError):
        import_profile({"format": PROFILE_IO_FORMAT, "profile": {"name": "  "}})


def test_from_json_rejects_bad_json() -> None:
    with pytest.raises(ProfileImportError):
        from_json("{not valid json")


def test_no_code_execution_paths_in_module() -> None:
    # Security boundary: imports are strictly data, never executed. Check for
    # actual call syntax so the module's own docstring prose doesn't trip this.
    source = Path(import_export.__file__).read_text(encoding="utf-8")
    for banned in ("exec(", "eval(", "__import__("):
        assert banned not in source
