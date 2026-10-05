"""Rewrite Quill Radio's installer registration block from the shared profile.

``standalone/radio/installer/quill-radio.iss`` is written by hand, except for
the lines between its generated-block marks, which register Quill Radio as a
media player. Those come from :data:`quill.core.windows_media.RADIO` through
``build_media_player_registry_lines`` -- the same profile Preferences > Make
Quill Radio My Media Player writes -- so the installer cannot offer a type the
app does not play.

    python scripts/sync_radio_installer_registry.py          # rewrite the block
    python scripts/sync_radio_installer_registry.py --check  # exit 1 on drift

The file's own line endings are kept.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ISS = REPO / "standalone" / "radio" / "installer" / "quill-radio.iss"
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from build_windows_distribution import build_media_player_registry_lines  # noqa: E402

from quill.core.windows_installer_lines import replace_block  # noqa: E402


def synced(text: str) -> str:
    newline = "\r\n" if "\r\n" in text else "\n"
    return replace_block(text, build_media_player_registry_lines(), newline=newline)


def main(argv: list[str]) -> int:
    raw = ISS.read_bytes().decode("utf-8")
    wanted = synced(raw)
    if "--check" in argv:
        if wanted != raw:
            print(f"{ISS.name}: the media-player registration block has drifted; run")
            print("python scripts/sync_radio_installer_registry.py")
            return 1
        return 0
    if wanted != raw:
        ISS.write_bytes(wanted.encode("utf-8"))
        print(f"Rewrote the registration block in {ISS.name}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
