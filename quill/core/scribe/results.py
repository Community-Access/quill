"""What happens to each Scribe output when it is ready (PRD section 9).

| Format | Default action | Where |
|---|---|---|
| HTML, Word, EPUB | open in the editor (rich) | ``editor`` |
| BRF | open in QUILL's braille view (QUILL opens a .brf as braille) | ``braille`` |
| MP3, DAISY | open in Media Player | ``player`` |
| Tagged PDF, MOBI, offline web page | saved; the sentence says where | ``save`` |

"Open each result when it is ready" decides whether the default action runs
or is only offered (7.7). wx-free.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

DEFAULT_ACTION: dict[str, str] = {
    "html": "editor",
    "docx": "editor",
    "epub": "editor",
    "brf": "braille",
    "mp3": "player",
    "daisy": "player",
    "pdf": "save",
    "mobi": "save",
    "offline_html": "save",
}

#: The open result's name in the sentence: "Word is open in QUILL".
OPENED_NAME: dict[str, str] = {
    "html": "The accessible HTML",
    "docx": "Word",
    "epub": "The EPUB",
    "brf": "The braille",
    "mp3": "The MP3 audio",
    "daisy": "The DAISY book",
}


def default_action(format_id: str) -> str:
    return DEFAULT_ACTION.get(format_id, "save")


def opened_phrase(format_id: str, where: str) -> str:
    """``"Word is open in QUILL"``."""
    return f"{OPENED_NAME.get(format_id, 'The result')} is open in {where}"


def daisy_entry(path: Path) -> Path | None:
    """The navigation file of a DAISY result: its ``.ncx`` (DAISY 3) or
    ``ncc.html`` (DAISY 2.02). A zip is unpacked beside itself first, into a
    folder of the same name, never outside it. Which DAISY Scribe writes is
    unconfirmed (PRD 16); both are looked for."""
    folder = path
    if path.is_file() and zipfile.is_zipfile(path):
        folder = path.with_suffix("")
        if not folder.exists():
            folder.mkdir(parents=True)
            with zipfile.ZipFile(path) as archive:
                for member in archive.infolist():
                    target = (folder / member.filename).resolve()
                    if folder.resolve() not in target.parents and target != folder.resolve():
                        continue  # a name that would leave the folder
                    archive.extract(member, folder)
    if not folder.is_dir():
        return None
    for pattern in ("*.ncx", "ncc.html", "NCC.HTML", "*.opf"):
        found = sorted(folder.rglob(pattern))
        if found:
            return found[0]
    return None


__all__ = ["DEFAULT_ACTION", "OPENED_NAME", "daisy_entry", "default_action", "opened_phrase"]
