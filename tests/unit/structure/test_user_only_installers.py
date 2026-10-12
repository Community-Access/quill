"""The shipped Cast, Radio and QUILL Lite installers install for one user."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
USER_ONLY_INSTALLERS = (
    REPO / "standalone" / "cast" / "installer" / "quill-cast.iss",
    REPO / "standalone" / "cast" / "installer" / "quill-cast-shared.iss",
    REPO / "standalone" / "radio" / "installer" / "quill-radio.iss",
    REPO / "standalone" / "quilllite" / "installer" / "quilllite.iss",
)


@pytest.mark.parametrize("installer", USER_ONLY_INSTALLERS, ids=lambda path: path.name)
def test_installer_cannot_offer_an_elevated_all_users_mode(installer: Path) -> None:
    source = installer.read_text(encoding="utf-8-sig")
    assert re.search(r"^PrivilegesRequired=lowest$", source, re.M), installer
    assert not re.search(r"^PrivilegesRequiredOverridesAllowed\s*=", source, re.M), installer
    assert re.search(r"^DefaultDirName=\{autopf\}", source, re.M), installer
