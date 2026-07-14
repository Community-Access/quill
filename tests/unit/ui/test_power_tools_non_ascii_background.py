"""Regression guard: Convert Non-ASCII to HTML Entities must not block the UI
thread (#906 -- a 1MB+ document froze QUILL, and the screen reader riding
along with it, for about a minute).

encode_all_non_ascii() used to run its per-character transform loop directly
on the calling (UI) thread via the shared, synchronous
_power_tools_transform_selection_or_document() helper. It now runs the
transform on a background thread via _run_background_task(), matching every
other potentially-slow operation in this codebase.
"""

from __future__ import annotations

from quill.ui.main_frame_power_tools import PowerToolsActionsMixin


class _Editor:
    def __init__(self, text: str) -> None:
        self._text = text
        self._sel = (0, 0)

    def GetValue(self) -> str:
        return self._text

    def GetSelection(self) -> tuple[int, int]:
        return self._sel

    def SetSelection(self, start: int, end: int) -> None:
        self._sel = (start, end)


class _Document:
    def __init__(self, encoding: str = "utf-8") -> None:
        self.source_metadata: dict[str, object] = {}
        self.path = None
        self.text = ""
        self.encoding = encoding

    def set_text(self, text: str) -> None:
        self.text = text


class _Harness(PowerToolsActionsMixin):
    def __init__(self, text: str, *, selection: tuple[int, int] = (0, 0)) -> None:
        self.editor = _Editor(text)
        self.editor._sel = selection
        self.document = _Document()
        self.status: str | None = None
        self.replaced: str | None = None
        self.background_calls: list[str] = []

    def _replace_document_text(self, updated_text: str) -> None:
        self.replaced = updated_text

    def _set_status(self, message: str) -> None:
        self.status = message

    def _run_background_task(self, label, work, on_success, **kwargs):  # noqa: ANN001
        # Deterministic stand-in for the real thread pool: run inline so the
        # test can assert on the result without a real background thread.
        self.background_calls.append(label)
        result = work(lambda *_a: None)
        on_success(result)


def test_encode_all_non_ascii_runs_on_a_background_task() -> None:
    harness = _Harness("café")
    harness.encode_all_non_ascii()
    assert harness.background_calls  # not run inline on the calling thread
    assert harness.replaced == "caf&eacute;"
    assert harness.document.text == "caf&eacute;"
    assert harness.status == "Converted non-ASCII characters to HTML entities"


def test_encode_all_non_ascii_only_transforms_the_selection() -> None:
    harness = _Harness("café résumé", selection=(0, 4))
    harness.encode_all_non_ascii()
    assert harness.replaced == "caf&eacute; résumé"


def test_encode_all_non_ascii_blocks_on_a_read_only_document() -> None:
    harness = _Harness("café")
    harness.document.source_metadata["read_only_guard"] = True
    harness.encode_all_non_ascii()
    assert not harness.background_calls
    assert harness.status == "Document is read-only"
    assert harness.replaced is None


def test_encode_all_non_ascii_drops_a_now_pointless_utf8_bom() -> None:
    """#905: a UTF-8 BOM only makes sense when the file still has multi-byte
    UTF-8 content. Once every non-ASCII character is an HTML entity, the
    result is pure ASCII, and saving with "utf-8-sig" would write a
    three-byte BOM prefix for content that is not UTF-8-specific at all."""
    harness = _Harness("café")
    harness.document.encoding = "utf-8-sig"
    harness.encode_all_non_ascii()
    assert harness.document.encoding == "utf-8"


def test_encode_all_non_ascii_keeps_the_bom_when_non_ascii_remains() -> None:
    # A partial-selection conversion can leave non-ASCII text elsewhere in the
    # document; the BOM is still meaningful then and must not be dropped.
    harness = _Harness("café résumé", selection=(0, 4))
    harness.document.encoding = "utf-8-sig"
    harness.document.text = "café résumé"
    harness.encode_all_non_ascii()
    assert harness.document.encoding == "utf-8-sig"
