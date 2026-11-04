"""axe-core is vendored, pinned and unchanged (wordpress.md 9.4).

Check This Page runs quill/data/axe/axe.min.js inside a hidden browser. The
file is the npm release named in SOURCE.json, byte for byte, with its licence
beside it, so an edit or a swapped copy fails here instead of shipping.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from quill.core.wordpress import page_audit

AXE = Path(page_audit.AXE_PATH)
SOURCE = json.loads((AXE.parent / "SOURCE.json").read_text(encoding="utf-8"))


def test_the_bundled_file_is_the_pinned_release() -> None:
    record = SOURCE["files"]["axe.min.js"]
    data = AXE.read_bytes()
    assert hashlib.sha256(data).hexdigest() == record["sha256"]
    assert len(data) == record["bytes"]
    assert SOURCE["version"] in data[:400].decode("utf-8", "replace")


def test_its_licences_ship_beside_it_and_the_notices_name_it() -> None:
    assert "Mozilla Public License" in (AXE.parent / "LICENSE.txt").read_text(encoding="utf-8")
    assert (AXE.parent / "LICENSE-3RD-PARTY.txt").is_file()
    catalogue = json.loads(
        Path("quill/data/third_party/components.json").read_text(encoding="utf-8")
    )
    entry = next(c for c in catalogue["components"] if c["id"] == "axe-core")
    assert entry["version"] == SOURCE["version"]


def test_check_this_page_finds_it() -> None:
    assert page_audit.axe_available()
