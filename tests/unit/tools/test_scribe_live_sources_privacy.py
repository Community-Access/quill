"""No personal value in the Scribe live-run test documents.

The documents in ``tests/corpus/scribe_live/`` are public. Office, the ODF
writers and the Python libraries all stamp names into metadata on their own:
the saving user's name and Windows account, the computer, a library's
template author. The builder sets every such field to one neutral value;
this test proves it on the committed bytes.

The personal values come from whoever runs the test -- the Windows user and
domain, the computer's name, and Office's user name and initials from the
registry -- never written here. In CI they are the runner's values, which
must not appear either. Each is searched for in the raw bytes, as ASCII and
as UTF-16LE (Office's binary property streams), regardless of case.
"""

from __future__ import annotations

import os
import re
import sys
import zipfile
from pathlib import Path

import pytest

FOLDER = Path(__file__).resolve().parents[2] / "corpus" / "scribe_live"
NEUTRAL = "QUILL test documents"
#: Template authors the libraries leave behind unless told otherwise. (A
#: program's own name in an Application field, "Openpyxl 3.1.5", is no person.)
LIBRARY_AUTHORS = ("python-docx", "Steve Canny")
#: Too short or too common to mean a person when found inside a file.
_MIN_LENGTH = 4


def _office_user() -> list[str]:
    if sys.platform != "win32":
        return []
    import winreg

    found: list[str] = []
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Office\Common\UserInfo"
        ) as key:
            for name in ("UserName", "UserInitials", "Company"):
                try:
                    value, _kind = winreg.QueryValueEx(key, name)
                except OSError:
                    continue
                found.append(str(value))
    except OSError:
        pass
    return found


def personal_values() -> list[str]:
    """This computer's own names: never in a committed test document."""
    values = [os.environ.get(n, "") for n in ("USERNAME", "USER", "USERDOMAIN", "COMPUTERNAME")]
    values += _office_user()
    words: set[str] = set()
    for value in values:
        value = value.strip()
        if len(value) >= _MIN_LENGTH:
            words.add(value)
        # "Bishop, Jeff - (jeffbis)": each name in it, as well as the whole.
        words.update(w for w in re.split(r"[^\w]+", value) if len(w) >= _MIN_LENGTH)
    return sorted(words, key=str.lower)


def _files() -> list[Path]:
    return sorted(p for p in FOLDER.iterdir() if p.is_file() and p.name.startswith("q"))


def _haystack(path: Path) -> bytes:
    """The file, and every member of it if it is a zip (OOXML, ODF, EPUB)."""
    raw = path.read_bytes()
    parts = [raw]
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            parts += [archive.read(name) for name in archive.namelist()]
    return b"\n".join(parts).lower()


def test_the_sources_are_all_here() -> None:
    assert len(_files()) == 30


@pytest.mark.parametrize("path", _files(), ids=lambda p: p.name)
def test_no_personal_name_is_in_a_test_document(path: Path) -> None:
    values = personal_values()
    if not values:
        pytest.skip("this computer gives no user, domain or computer name to look for")
    haystack = _haystack(path)
    found = [
        "one of this computer's names"  # never the value itself, in a public log
        for value in values
        if value.lower().encode("utf-8") in haystack
        or value.lower().encode("utf-16-le") in haystack
    ]
    assert not found, f"{path.name} carries {len(found)} of this computer's own names"


@pytest.mark.parametrize("path", _files(), ids=lambda p: p.name)
def test_every_author_field_is_ours(path: Path) -> None:
    haystack = _haystack(path)
    for author in LIBRARY_AUTHORS:
        assert author.lower().encode() not in haystack, f"{path.name} names {author}"
    if not zipfile.is_zipfile(path):
        return
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        for member, pattern in (
            ("docProps/core.xml", r"<(dc:creator|cp:lastModifiedBy)>([^<]*)<"),
            ("meta.xml", r"<(dc:creator|meta:initial-creator)>([^<]*)<"),
        ):
            if member in names:
                text = archive.read(member).decode("utf-8", errors="replace")
                for field, value in re.findall(pattern, text):
                    assert value in (NEUTRAL, ""), f"{path.name} {field} is {value!r}"
        if "docProps/app.xml" in names:
            app = archive.read("docProps/app.xml").decode("utf-8", errors="replace")
            for field, value in re.findall(r"<(Company|Manager)>([^<]*)<", app):
                assert value in (NEUTRAL, ""), f"{path.name} {field} is {value!r}"


def test_the_personal_values_are_split_into_names(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("USERNAME", "USER", "USERDOMAIN", "COMPUTERNAME"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("USERNAME", "Doe, Alex - (adoe)")
    monkeypatch.setattr(sys.modules[__name__], "_office_user", lambda: ["AD"])
    assert {"Alex", "adoe"} <= set(personal_values())
    assert "AD" not in personal_values()  # initials are too short to search for
