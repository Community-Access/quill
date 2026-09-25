"""A cache the running app needs must not land in another product's folder.

``quill/core/lite/paths.py`` opens by saying QUILL Lite is "deliberately **not**
``%APPDATA%\\Quill``", and ``core/lite/settings.py`` that "a machine that has
never had QUILL installed must not grow a Quill data folder because somebody
opened a text file". Both were untrue until 2026-09-15: two shared-core caches
resolved through :func:`app_data_dir`, which is QUILL's folder, and QUILL Lite
reaches both on its first window --

* the comtypes generated-wrapper cache, because the native Rich Edit surface
  goes through COM; and
* the managed Hunspell dir, because the spell checker asks for it.

One ``--check`` -- less than opening a document -- created
``%APPDATA%\\Quill\\comtypes_gen`` and ``%APPDATA%\\Quill\\spell``.

The fix is a seam, not an override. :func:`app_data_dir` still means *QUILL's*
folder, because QUILL Lite reaches it on purpose in three places (share QUILL's
dictionary, share QUILL's abbreviations, list QUILL's sound schemes) and a
global redirect would have broken all three silently -- which is the test at the
bottom of this file.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from quill.core import paths


@pytest.fixture(autouse=True)
def _no_declaration_leaks_between_tests() -> Iterator[None]:
    """The declaration is process-wide, so put it back however the test left it."""
    previous = paths._RUNNING_APP_DATA_DIR
    try:
        yield
    finally:
        paths.use_running_app_data_dir(previous)


def test_an_app_that_declares_nothing_gets_quills_folder() -> None:
    """The default, and therefore every app except QUILL Lite: unchanged."""
    assert paths.running_app_data_dir() == paths.app_data_dir()


def test_a_declared_folder_is_where_the_running_app_writes(tmp_path: Path) -> None:
    lite = tmp_path / "QuillLite"
    paths.use_running_app_data_dir(lambda: lite)
    assert paths.running_app_data_dir() == lite


def test_declaring_one_does_not_move_quills_own_folder(tmp_path: Path) -> None:
    """The whole point of the seam. ``app_data_dir`` keeps meaning QUILL's."""
    quill_dir = paths.app_data_dir()
    paths.use_running_app_data_dir(lambda: tmp_path / "QuillLite")
    assert paths.app_data_dir() == quill_dir


def test_a_provider_that_raises_falls_back_rather_than_losing_the_cache() -> None:
    """A cache is a convenience; a crash while locating one is not acceptable.

    comtypes falls back to in-memory codegen if the folder cannot be resolved
    at all, so the cost of a bad declaration is a slower COM call -- but the
    right answer is still QUILL's folder, which is where these caches lived
    before the seam existed.
    """

    def _broken() -> Path:
        raise RuntimeError("no data dir today")

    paths.use_running_app_data_dir(_broken)
    assert paths.running_app_data_dir() == paths.app_data_dir()


def test_the_managed_spell_dir_follows_the_running_app(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``spell/`` is one of the two folders that leaked."""
    from quill.core import spell_languages

    monkeypatch.delenv("QUILL_APP_ROOT", raising=False)  # no bundled dictionaries
    lite = tmp_path / "QuillLite"
    paths.use_running_app_data_dir(lambda: lite)
    assert spell_languages.managed_spell_dir() == lite / "spell"
    assert spell_languages.managed_hunspell_dir() == lite / "spell" / "hunspell"


def test_the_comtypes_cache_follows_the_running_app(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``comtypes_gen/`` is the other, and the one QUILL Lite cannot avoid: it is
    created by the native Rich Edit surface, on the first window."""
    from quill.platform.windows import comtypes_setup

    class _FakeComtypesClient:
        gen_dir: str | None = "somewhere else"

    monkeypatch.setattr(comtypes_setup, "_cc", _FakeComtypesClient, raising=False)
    monkeypatch.setattr(comtypes_setup, "_redirected", False, raising=False)
    lite = tmp_path / "QuillLite"
    paths.use_running_app_data_dir(lambda: lite)

    comtypes_setup.ensure_comtypes_gen_dir_redirected()

    assert _FakeComtypesClient.gen_dir == str(lite / "comtypes_gen")
    assert (lite / "comtypes_gen").is_dir()


def test_quilllite_still_reaches_quills_folder_when_asked_to_share(
    tmp_path: Path,
) -> None:
    """The three deliberate crossings, which a global override would have broken.

    ``share_quill_dictionary`` and ``share_quill_abbreviations`` are Preferences
    switches whose entire meaning is "use QUILL's copy". They resolve through
    ``app_data_dir`` and must keep doing so while QUILL Lite is declaring its own
    folder for everything else.
    """
    from quill.core.lite.spelling import dictionary_dir

    paths.use_running_app_data_dir(lambda: tmp_path / "QuillLite")

    class _Sharing:
        share_quill_dictionary = True

    class _NotSharing:
        share_quill_dictionary = False

    own = tmp_path / "QuillLite"
    assert dictionary_dir(_Sharing(), own) == paths.app_data_dir()
    assert dictionary_dir(_NotSharing(), own) == own
