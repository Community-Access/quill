"""Spelling: whose dictionary, and when the checker keeps quiet.

The checking itself is QUILL's and is tested against QUILL. What is tested here
is the two decisions QUILL Lite adds, because both are the kind that fail
silently:

* **The file-type rule.** A live checker in ``settings.json`` flags every key
  and one in ``main.py`` flags every identifier. Getting this wrong does not
  crash anything -- it produces an editor that interrupts constantly in exactly
  the files where it has nothing useful to say, which a sighted tester
  experiences as mild noise and a screen-reader user experiences as unusable.
* **Whose folder the taught words land in.** A machine that has never had QUILL
  installed must not grow a ``%APPDATA%\\Quill`` because somebody taught a text
  editor a word. That is invisible until somebody uninstalls QUILL Lite and finds
  a Quill folder they never asked for.

wx-free, against real files in a temporary directory.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from quill.core.lite import spelling as spelling_mod
from quill.core.lite.features import AREAS
from quill.core.lite.settings import Settings
from quill.core.spellcheck_filetypes import CODE_SUFFIXES, is_code_filename


@pytest.fixture
def data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("QUILL_LITE_DATA_DIR", str(tmp_path))
    return tmp_path


# --------------------------------------------------------------------------- #
# The file-type rule
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "name",
    ["letter.txt", "notes.md", "report.rtf", "README", "a.markdown", "diary"],
)
def test_prose_is_checked(name: str) -> None:
    assert spelling_mod.initial_live_check(Path(name)) is True
    assert spelling_mod.skipped_as_code(Path(name)) is False


@pytest.mark.parametrize(
    "name",
    ["main.py", "settings.json", "app.js", "style.css", "build.ps1", "server.log"],
)
def test_code_is_not(name: str) -> None:
    assert spelling_mod.initial_live_check(Path(name)) is False
    assert spelling_mod.skipped_as_code(Path(name)) is True


def test_markdown_is_prose_not_code() -> None:
    """The one extension that looks like code and is not.

    Markdown is where people write. Its fenced blocks and inline code spans are
    handled by suppressing the *region* (quill.core.spellcheck_live), which is
    the right granularity -- suppressing the whole file would silence the prose
    around the code, which is the part worth checking.
    """
    assert ".md" not in CODE_SUFFIXES
    assert spelling_mod.initial_live_check(Path("README.md")) is True


def test_an_unnamed_document_is_checked() -> None:
    """A new document has no extension to judge, and prose is the safer guess.

    A spurious alert in a scratch buffer is a smaller loss than silence in the
    letter somebody is actually writing.
    """
    assert spelling_mod.initial_live_check(None) is True
    assert spelling_mod.skipped_as_code(None) is False


def test_the_extension_is_matched_regardless_of_case() -> None:
    """Windows hands back whatever case the file was created with."""
    assert is_code_filename("SETUP.PY") is True
    assert is_code_filename(Path("Config.JSON")) is True


def test_a_dotless_name_is_not_read_as_an_extension() -> None:
    """``.env`` is code; a file merely *called* env is not."""
    assert is_code_filename("env") is False
    assert is_code_filename(".env") is False  # a bare dotfile has no suffix
    assert is_code_filename("local.env") is True


# --------------------------------------------------------------------------- #
# Whose dictionary
# --------------------------------------------------------------------------- #


def test_taught_words_stay_in_quilllites_own_folder_by_default(data_dir: Path) -> None:
    """The whole point of the switch being off by default."""
    settings = Settings()
    assert settings.share_quill_dictionary is False
    assert spelling_mod.dictionary_dir(settings, data_dir) == data_dir

    assert spelling_mod.add_word("Bhattacharya", settings, data_dir, None) is True
    written = data_dir / "dictionaries" / "personal.json"
    assert written.is_file()
    assert "bhattacharya" in json.loads(written.read_text(encoding="utf-8"))


def test_the_share_switch_points_at_quills_folder(data_dir: Path) -> None:
    from quill.core.paths import app_data_dir

    settings = Settings()
    settings.share_quill_dictionary = True
    assert spelling_mod.dictionary_dir(settings, data_dir) == app_data_dir()


def test_a_taught_word_is_known_afterwards(data_dir: Path) -> None:
    settings = Settings()
    assert "quillville" not in spelling_mod.load_dictionary(settings, data_dir, None)
    spelling_mod.add_word("QuillVille", settings, data_dir, None)
    assert "quillville" in spelling_mod.load_dictionary(settings, data_dir, None)


def test_the_documents_own_sidecar_dictionary_is_read(data_dir: Path, tmp_path: Path) -> None:
    """A word taught for one document does not leak into every document."""
    document = tmp_path / "thesis.txt"
    document.write_text("x", encoding="utf-8")
    sidecar = document.with_suffix(document.suffix + ".quill-dict.json")
    sidecar.write_text(json.dumps(["hapaxlegomenon"]), encoding="utf-8")

    settings = Settings()
    assert "hapaxlegomenon" in spelling_mod.load_dictionary(settings, data_dir, document)
    assert "hapaxlegomenon" not in spelling_mod.load_dictionary(settings, data_dir, None)


def test_a_corrupt_dictionary_is_an_empty_one_not_an_exception(data_dir: Path) -> None:
    """An editor that will not open a file over a bad word list loses work."""
    path = data_dir / "dictionaries" / "personal.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{{{ not json at all %%%", encoding="utf-8")
    assert spelling_mod.load_dictionary(Settings(), data_dir, None) == set()


def test_add_word_reports_failure_rather_than_raising(
    data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A read-only profile is a real situation, not a dialog-worthy error."""

    def _boom(*_args: object, **_kwargs: object) -> None:
        raise OSError("read-only")

    monkeypatch.setattr("quill.core.spellcheck.add_word_to_scope", _boom)
    assert spelling_mod.add_word("word", Settings(), data_dir, None) is False


# --------------------------------------------------------------------------- #
# The area, and the settings that go with it
# --------------------------------------------------------------------------- #


def test_spelling_is_a_switchable_area_that_starts_on() -> None:
    from quill.core.lite.features import DEFAULT_OFF

    labels = {area.id: area.label for area in AREAS}
    assert labels["spelling"] == "Spell check"
    assert "spelling" not in DEFAULT_OFF


def test_the_two_new_settings_round_trip(tmp_path: Path) -> None:
    from quill.core.lite import settings as settings_mod

    settings = Settings()
    settings.share_quill_dictionary = True
    settings.spell_check_while_typing = False
    path = tmp_path / "settings.json"
    settings_mod.save(settings, path)

    reloaded = settings_mod.load(path)
    assert reloaded.share_quill_dictionary is True
    assert reloaded.spell_check_while_typing is False


def test_a_default_profile_writes_neither_setting(tmp_path: Path) -> None:
    """The delta store's whole promise, checked on the new fields too."""
    from quill.core.lite import settings as settings_mod

    path = tmp_path / "settings.json"
    settings_mod.save(Settings(), path)
    assert json.loads(path.read_text(encoding="utf-8")) == {"schema": settings_mod.SCHEMA}
