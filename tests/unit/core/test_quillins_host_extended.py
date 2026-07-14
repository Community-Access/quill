"""Unit tests for the new API capabilities added in the capability expansion.

Covers: get_cursor_offset, get_selection_range, set_cursor, replace_range,
set_status, show_choices, and the storage trio (get/set/delete). Tests drive
ApiDispatcher directly without spawning a worker subprocess so the security
gate is tested in tight isolation — exactly the same approach as
test_quillins_host.py.
"""

from __future__ import annotations

from typing import Any

from quill.core.quillins.host import ApiDispatcher
from quill.core.quillins.model import (
    CAP_EDITOR_READ,
    CAP_EDITOR_WRITE,
    CAP_STORAGE,
    CAP_UI_CHOICES,
    CAP_UI_STATUS,
    Contributions,
    ExtensionManifest,
)


class _RecordingServices:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[Any, ...]]] = []
        self._cursor_offset = 5
        self._selection = {"start": 3, "end": 8}

    # -- editor.read ----------------------------------------------------------
    def get_text(self) -> str:
        return "hello world"

    def get_selection(self) -> str:
        return "lo wo"

    def get_cursor(self) -> dict[str, int]:
        return {"line": 1, "column": 6, "percent": 45}

    def get_cursor_offset(self) -> int:
        self.calls.append(("get_cursor_offset", ()))
        return self._cursor_offset

    def get_selection_range(self) -> dict[str, int]:
        self.calls.append(("get_selection_range", ()))
        return dict(self._selection)

    # -- editor.write ---------------------------------------------------------
    def insert_text(self, text: str) -> None:
        self.calls.append(("insert_text", (text,)))

    def replace_selection(self, text: str) -> None:
        self.calls.append(("replace_selection", (text,)))

    def set_text(self, text: str) -> None:
        self.calls.append(("set_text", (text,)))

    def open_buffer(self, text: str, title: str) -> None:
        self.calls.append(("open_buffer", (text, title)))

    def set_cursor(self, offset: int) -> None:
        self.calls.append(("set_cursor", (offset,)))
        self._cursor_offset = offset

    def replace_range(self, start: int, end: int, text: str) -> None:
        self.calls.append(("replace_range", (start, end, text)))

    # -- ui -------------------------------------------------------------------
    def announce(self, message: str) -> None:
        self.calls.append(("announce", (message,)))

    def is_verbosity_speech_enabled(self) -> bool:
        return True

    def prompt(self, title: str, label: str, default: str) -> str | None:
        return None

    def set_status(self, message: str) -> None:
        self.calls.append(("set_status", (message,)))

    def show_choices(self, title: str, items: list[str]) -> str | None:
        self.calls.append(("show_choices", (title, items)))
        return items[0] if items else None

    # -- fs/net/clipboard -----------------------------------------------------
    def read_file(self, path: str) -> str:
        return ""

    def write_file(self, path: str, text: str) -> None:
        pass

    def fetch(self, url: str, method: str, body: str | None) -> dict[str, Any]:
        return {}

    def get_clipboard(self) -> str:
        return ""

    def set_clipboard(self, text: str) -> None:
        pass


def _manifest(*capabilities: str) -> ExtensionManifest:
    return ExtensionManifest(
        id="com.test.ext",
        name="Test",
        version="1.0.0",
        capabilities=tuple(capabilities),
        main="extension.py",
        contributes=Contributions(),
    )


def _call(dispatcher: ApiDispatcher, method: str, *args: Any) -> dict[str, Any]:
    return dispatcher.handle({"type": "api_call", "id": 1, "method": method, "args": list(args)})


# -- get_cursor_offset --------------------------------------------------------


def test_get_cursor_offset_returns_integer() -> None:
    services = _RecordingServices()
    dispatcher = ApiDispatcher(_manifest(CAP_EDITOR_READ), services)
    result = _call(dispatcher, "get_cursor_offset")
    assert result["ok"] is True
    assert result["value"] == 5
    assert ("get_cursor_offset", ()) in services.calls


def test_get_cursor_offset_requires_editor_read() -> None:
    dispatcher = ApiDispatcher(_manifest(), _RecordingServices())
    result = _call(dispatcher, "get_cursor_offset")
    assert result["ok"] is False
    assert result["error_kind"] == "CapabilityError"


# -- get_selection_range ------------------------------------------------------


def test_get_selection_range_returns_start_end_dict() -> None:
    services = _RecordingServices()
    dispatcher = ApiDispatcher(_manifest(CAP_EDITOR_READ), services)
    result = _call(dispatcher, "get_selection_range")
    assert result["ok"] is True
    assert result["value"] == {"start": 3, "end": 8}


def test_get_selection_range_requires_editor_read() -> None:
    dispatcher = ApiDispatcher(_manifest(), _RecordingServices())
    assert _call(dispatcher, "get_selection_range")["ok"] is False


# -- set_cursor ---------------------------------------------------------------


def test_set_cursor_moves_to_offset() -> None:
    services = _RecordingServices()
    dispatcher = ApiDispatcher(_manifest(CAP_EDITOR_WRITE), services)
    result = _call(dispatcher, "set_cursor", 7)
    assert result["ok"] is True
    assert ("set_cursor", (7,)) in services.calls


def test_set_cursor_requires_editor_write() -> None:
    dispatcher = ApiDispatcher(_manifest(CAP_EDITOR_READ), _RecordingServices())
    assert _call(dispatcher, "set_cursor", 0)["ok"] is False


# -- replace_range ------------------------------------------------------------


def test_replace_range_invokes_service_with_correct_args() -> None:
    services = _RecordingServices()
    dispatcher = ApiDispatcher(_manifest(CAP_EDITOR_WRITE), services)
    result = _call(dispatcher, "replace_range", 2, 7, "NEW")
    assert result["ok"] is True
    assert ("replace_range", (2, 7, "NEW")) in services.calls


def test_replace_range_requires_editor_write() -> None:
    dispatcher = ApiDispatcher(_manifest(CAP_EDITOR_READ), _RecordingServices())
    assert _call(dispatcher, "replace_range", 0, 5, "x")["ok"] is False


# -- set_status ---------------------------------------------------------------


def test_set_status_reaches_service() -> None:
    services = _RecordingServices()
    dispatcher = ApiDispatcher(_manifest(CAP_UI_STATUS), services)
    result = _call(dispatcher, "set_status", "3 matches found")
    assert result["ok"] is True
    assert ("set_status", ("3 matches found",)) in services.calls


def test_set_status_requires_ui_status() -> None:
    dispatcher = ApiDispatcher(_manifest(CAP_UI_CHOICES), _RecordingServices())
    assert _call(dispatcher, "set_status", "hi")["ok"] is False


def test_set_status_is_not_consent_gated() -> None:
    prompted = False

    def consent(cap: str, detail: str) -> bool:
        nonlocal prompted
        prompted = True
        return True

    services = _RecordingServices()
    dispatcher = ApiDispatcher(_manifest(CAP_UI_STATUS), services, consent=consent)
    _call(dispatcher, "set_status", "hello")
    assert not prompted


# -- show_choices -------------------------------------------------------------


def test_show_choices_returns_first_item() -> None:
    services = _RecordingServices()
    dispatcher = ApiDispatcher(_manifest(CAP_UI_CHOICES), services)
    result = _call(dispatcher, "show_choices", "Pick one", ["alpha", "beta", "gamma"])
    assert result["ok"] is True
    assert result["value"] == "alpha"
    assert services.calls[0] == ("show_choices", ("Pick one", ["alpha", "beta", "gamma"]))


def test_show_choices_empty_list_returns_none() -> None:
    services = _RecordingServices()
    dispatcher = ApiDispatcher(_manifest(CAP_UI_CHOICES), services)
    result = _call(dispatcher, "show_choices", "Pick one", [])
    assert result["ok"] is True
    assert result["value"] is None


def test_show_choices_requires_ui_choices() -> None:
    dispatcher = ApiDispatcher(_manifest(CAP_UI_STATUS), _RecordingServices())
    assert _call(dispatcher, "show_choices", "Pick", ["a"])["ok"] is False


# -- storage ------------------------------------------------------------------


def test_storage_roundtrip_within_session() -> None:
    services = _RecordingServices()
    dispatcher = ApiDispatcher(_manifest(CAP_STORAGE), services)
    assert _call(dispatcher, "get_storage", "counter")["value"] is None

    _call(dispatcher, "set_storage", "counter", "42")
    result = _call(dispatcher, "get_storage", "counter")
    assert result["ok"] is True
    assert result["value"] == "42"


def test_storage_delete_removes_key() -> None:
    services = _RecordingServices()
    dispatcher = ApiDispatcher(_manifest(CAP_STORAGE), services)
    _call(dispatcher, "set_storage", "k", "v")
    _call(dispatcher, "delete_storage", "k")
    assert _call(dispatcher, "get_storage", "k")["value"] is None


def test_storage_delete_missing_key_is_noop() -> None:
    dispatcher = ApiDispatcher(_manifest(CAP_STORAGE), _RecordingServices())
    result = _call(dispatcher, "delete_storage", "nonexistent")
    assert result["ok"] is True


def test_storage_requires_storage_capability() -> None:
    dispatcher = ApiDispatcher(_manifest(CAP_EDITOR_READ), _RecordingServices())
    assert _call(dispatcher, "get_storage", "k")["ok"] is False
    assert _call(dispatcher, "set_storage", "k", "v")["ok"] is False
    assert _call(dispatcher, "delete_storage", "k")["ok"] is False


def test_storage_is_isolated_per_dispatcher_instance() -> None:
    services = _RecordingServices()
    d1 = ApiDispatcher(_manifest(CAP_STORAGE), services)
    d2 = ApiDispatcher(_manifest(CAP_STORAGE), services)
    _call(d1, "set_storage", "x", "from-d1")
    assert _call(d2, "get_storage", "x")["value"] is None


def test_external_storage_dict_is_shared() -> None:
    shared: dict[str, str] = {}
    services = _RecordingServices()
    d1 = ApiDispatcher(_manifest(CAP_STORAGE), services, storage=shared)
    d2 = ApiDispatcher(_manifest(CAP_STORAGE), services, storage=shared)
    _call(d1, "set_storage", "key", "value")
    assert _call(d2, "get_storage", "key")["value"] == "value"


# -- capability constants are in CAPABILITIES ---------------------------------


def test_new_capabilities_are_in_the_catalogue() -> None:
    from quill.core.quillins.model import CAPABILITIES

    assert CAP_UI_STATUS in CAPABILITIES
    assert CAP_UI_CHOICES in CAPABILITIES
    assert CAP_STORAGE in CAPABILITIES
