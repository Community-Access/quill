"""Ctrl+S must not speak the word count twice (two Quillins, one number).

A user reported NVDA saying the same count twice in two phrasings after every
save: "386 words" then "Words: 386". Neither utterance was wrong on its own --
they came from two *different* bundled Quillins that both subscribe to
``document.after_save`` and both ship enabled:

* ``journal-stamp`` announced ``"Saved. 386 words."`` (``wordcount_mode``
  defaulted to ``always``), and
* ``status-scribe`` pushed ``"Words: 386"`` through ``api.set_status``, which
  on the editor host also reached the spoken channel -- so it spoke even though
  its own ``announce_on_save`` preference was off.

Nobody designed the combination; it fell out of two defaults meeting. These
tests walk *every* bundled Quillin that subscribes to ``document.after_save``,
so a fourth one that starts narrating counts on save fails here rather than in
somebody's ears.
"""

from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path
from typing import Any

from quill.core.quillins.loader import bundled_extensions_root

#: "386 words", "Words: 386", "Chars: 12" -- any count read out to the user.
_COUNT_PATTERN = re.compile(r"(\b\d+\s+(?:words?|chars?|characters?|sentences?)\b)|(\b\w+:\s*\d+)")


def _looks_like_a_count(message: str) -> bool:
    return _COUNT_PATTERN.search(message) is not None


def _manifest_defaults(raw: dict[str, Any]) -> dict[str, Any]:
    """Flatten a manifest's declared preference defaults into ``{key: default}``."""

    defaults: dict[str, Any] = {}
    for page in raw.get("contributes", {}).get("preferences", []):
        for tab in page.get("tabs", []):
            for section in tab.get("sections", []):
                for setting in section.get("settings", []):
                    key = setting.get("key")
                    if isinstance(key, str) and key:
                        defaults[key] = setting.get("default")
    return defaults


class _FakeApi:
    """A Quillin API handle that answers with the manifest's own defaults.

    Anything the Quillin says lands in :attr:`announced`; anything it displays
    lands in :attr:`statused`. Keeping the two apart is the whole point -- the
    bug was a display call arriving on the speech channel.
    """

    def __init__(self, defaults: dict[str, Any], text: str, overrides: dict[str, Any]) -> None:
        self._defaults = defaults
        self._overrides = overrides
        self._text = text
        self.announced: list[str] = []
        self.statused: list[str] = []

    def get_setting(self, key: str, default: Any = None) -> Any:
        if key in self._overrides:
            return self._overrides[key]
        if key in self._defaults and self._defaults[key] is not None:
            return self._defaults[key]
        return default

    def get_text(self) -> str:
        return self._text

    def announce(self, message: str) -> None:
        self.announced.append(message)

    def set_status(self, message: str) -> None:
        self.statused.append(message)

    def log(self, message: str) -> None:
        pass

    def insert_text(self, text: str) -> None:
        pass


def _after_save_handlers() -> list[tuple[str, Any, dict[str, Any]]]:
    """Return ``[(quillin_dir_name, handler, manifest_defaults), ...]``.

    Only entries that ship enabled (``enabled_by_default``) count: a handler the
    user must switch on is an opt-in, not a surprise.
    """

    found: list[tuple[str, Any, dict[str, Any]]] = []
    for directory in sorted(bundled_extensions_root().iterdir()):
        manifest_path = directory / "manifest.json"
        if not manifest_path.is_file():
            continue
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
        entries = [
            entry
            for entry in raw.get("contributes", {}).get("document_events", [])
            if isinstance(entry, dict)
            and entry.get("event") == "document.after_save"
            and entry.get("enabled_by_default", True)
        ]
        if not entries:
            continue
        main = raw.get("main", "extension.py")
        source = directory / main
        if source.suffix != ".py" or not source.is_file():
            continue
        spec = importlib.util.spec_from_file_location(f"{directory.name}_ext", source)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        defaults = _manifest_defaults(raw)
        for entry in entries:
            handler = getattr(module, str(entry["handler"]), None)
            assert callable(handler), f"{directory.name}: missing handler {entry['handler']}"
            found.append((directory.name, handler, defaults))
    return found


def _run_all_after_save(
    saved_file: Path, text: str, overrides: dict[str, dict[str, Any]] | None = None
) -> dict[str, _FakeApi]:
    """Fire every bundled ``document.after_save`` handler over one saved document."""

    per_quillin = overrides or {}
    event = {
        "file_path": str(saved_file),
        "extension": saved_file.suffix.lower(),
        "title": saved_file.name,
    }
    apis: dict[str, _FakeApi] = {}
    for name, handler, defaults in _after_save_handlers():
        api = _FakeApi(defaults, text, per_quillin.get(name, {}))
        handler(api, dict(event))
        apis[name] = api
    return apis


def _saved_document(tmp_path: Path, words: int) -> tuple[Path, str]:
    text = " ".join(f"word{index}" for index in range(words))
    path = tmp_path / "untitled.md"
    path.write_text(text, encoding="utf-8")
    return path, text


def test_bundled_after_save_handlers_are_found() -> None:
    """Guard the guard: an empty sweep would make every test below vacuous."""

    names = [name for name, _handler, _defaults in _after_save_handlers()]
    assert {"journal-stamp", "status-scribe"}.issubset(set(names)), (
        f"expected the two word-count Quillins among after_save subscribers, got {names}"
    )


def test_a_default_save_speaks_no_word_count(tmp_path: Path) -> None:
    """The reported bug: two counts, two phrasings, on a plain Ctrl+S."""

    path, text = _saved_document(tmp_path, 386)
    apis = _run_all_after_save(path, text)

    spoken = [(name, msg) for name, api in apis.items() for msg in api.announced]
    counts = [(name, msg) for name, msg in spoken if _looks_like_a_count(msg)]
    assert counts == [], (
        "A save with stock settings must not speak a word count. QUILL already "
        f"says 'Saved <name>'; these Quillins added more: {counts}"
    )


def test_no_after_save_handler_speaks_through_set_status(tmp_path: Path) -> None:
    """``api.set_status`` updates a cell. Speaking is ``api.announce``'s job.

    ``set_status`` is display-only on the host now, but a Quillin that pushes a
    count into the status bar on every save is still relying on a side channel
    to be heard -- exactly the coupling that produced the duplicate.
    """

    path, text = _saved_document(tmp_path, 386)
    apis = _run_all_after_save(path, text)

    pushed = {name: api.statused for name, api in apis.items() if api.statused}
    assert pushed == {}, (
        f"after_save must not push status text; the status cell handler already "
        f"refreshes it when the host renders the bar. Offenders: {pushed}"
    )


def test_at_most_one_count_is_spoken_when_the_user_opts_in(tmp_path: Path) -> None:
    """Opting both Quillins in is allowed -- but each speaks once, not twice."""

    path, text = _saved_document(tmp_path, 386)
    apis = _run_all_after_save(
        path,
        text,
        overrides={
            "journal-stamp": {"wordcount_mode": "always"},
            "status-scribe": {"announce_on_save": True},
        },
    )

    for name, api in apis.items():
        counts = [msg for msg in api.announced if _looks_like_a_count(msg)]
        assert len(counts) <= 1, f"{name} spoke the count more than once: {counts}"


def test_journal_stamp_does_not_repeat_the_hosts_saved_prefix(tmp_path: Path) -> None:
    """``MainFrame.save_file`` already announced "Saved <name>" before this ran."""

    path, text = _saved_document(tmp_path, 386)
    apis = _run_all_after_save(
        path, text, overrides={"journal-stamp": {"wordcount_mode": "always"}}
    )

    spoken = apis["journal-stamp"].announced
    assert spoken, "journal-stamp should still announce the count when asked to"
    assert not any(msg.lower().startswith("saved") for msg in spoken), (
        f"the host says 'Saved <name>'; journal-stamp must not lead with it too: {spoken}"
    )
    assert any("386 words" in msg for msg in spoken), spoken
