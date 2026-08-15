"""Tests for quill.io.pages -- M-9 thread-safety, and the codec patch that aged out.

The lock test is the M-9 regression: ``_patched_id_name_map()`` temporarily
replaces a module-global dict, and two documents opening at once must not
corrupt each other's map.

The second test is the one this file needed and did not have. keynote-parser
1.14 removed ``ID_NAME_MAP`` entirely -- it handles an unknown archive type
itself now -- and QUILL patched it unconditionally, so the fallback that existed
to *prevent* a crash had become the crash: every .pages file opened against a
current install raised AttributeError. The fake codec here has the attribute and
so exercised the old path forever, which is exactly why nothing caught it.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch


def _keynote_modules(codec: MagicMock, file_utils: MagicMock) -> dict[str, MagicMock]:
    """A complete fake keynote-parser, so these tests never need the real one.

    Two traps, and both let the tests pass while measuring nothing:

    * ``import keynote_parser.codec`` imports the **parent** package first, so
      patching only the submodules leaves the real import to succeed or fail by
      accident of what is installed. On a machine without this optional
      dependency the ImportError is swallowed by the code under test and the
      assertions never run.
    * ``import a.b as x`` binds ``getattr(sys.modules["a"], "b")``, not
      ``sys.modules["a.b"]`` -- and a bare ``MagicMock`` parent happily invents
      a *different* ``codec`` on demand. The parent's attributes must point at
      the very objects being patched in.
    """
    parent = MagicMock()
    parent.codec = codec
    parent.file_utils = file_utils
    return {
        "keynote_parser": parent,
        "keynote_parser.codec": codec,
        "keynote_parser.file_utils": file_utils,
    }


def test_concurrent_reads_serialize_via_lock(tmp_path: Path) -> None:
    # M-9: _patched_id_name_map() temporarily replaces a global dict; concurrent
    # reads must not corrupt each other's map. The lock ensures they serialize.
    import quill.io.pages as _pages

    call_order: list[str] = []

    def slow_parse(path, reader):
        call_order.append("enter")
        time.sleep(0.02)
        call_order.append("exit")
        return {}

    errors: list[Exception] = []

    # ONE codec module, shared by every thread -- which is the situation the
    # lock exists for. A per-thread fake would give each thread its own lock
    # and the test would pass while serializing nothing.
    fake_codec = MagicMock()
    fake_codec.ID_NAME_MAP = {}
    fake_codec._quill_id_name_map_lock = threading.Lock()
    fake_file_utils = MagicMock()
    mods = _keynote_modules(fake_codec, fake_file_utils)

    def _open(i: int) -> None:
        try:
            with patch.dict("sys.modules", mods):
                with patch.object(_pages, "_parse_iwa_bundle", slow_parse):
                    try:
                        _pages._read_pages_via_iwa(tmp_path / f"doc{i}.pages")
                    except (ImportError, ValueError):
                        pass  # expected — no real .pages file
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=_open, args=(i,)) for i in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5)

    assert not errors, f"Thread errors: {errors}"
    # No interleaved enter/exit pairs — each enter is immediately followed by exit.
    for idx in range(0, len(call_order) - 1, 2):
        assert call_order[idx] == "enter"
        assert call_order[idx + 1] == "exit"


def test_a_codec_without_the_old_map_is_left_alone(tmp_path: Path) -> None:
    """keynote-parser 1.14+ has no ID_NAME_MAP, and must not be patched.

    Patching it unconditionally is an AttributeError on every .pages file
    opened against a current install. The newer library handles an unknown
    archive type itself, which is what the patch existed to do.
    """
    import quill.io.pages as _pages

    seen: list[bool] = []

    def _parse(path, reader):
        import keynote_parser.codec as codec

        seen.append(hasattr(codec, "ID_NAME_MAP"))
        return {}

    modern_codec = MagicMock()
    del modern_codec.ID_NAME_MAP  # a MagicMock invents attributes; this one must not
    modern_codec._quill_id_name_map_lock = threading.Lock()
    mods = _keynote_modules(modern_codec, MagicMock())
    with patch.dict("sys.modules", mods), patch.object(_pages, "_parse_iwa_bundle", _parse):
        try:
            _pages._read_pages_via_iwa(tmp_path / "doc.pages")
        except (ImportError, ValueError):
            pass  # expected -- the parse returns nothing, so there is no text

    # The parse ran (rather than blowing up before it), and nothing was patched in.
    assert seen == [False]
