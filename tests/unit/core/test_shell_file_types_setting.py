"""The "File types offered to QUILL" setting decides which files get right-click verbs.

Until 2026-10 nothing read ``shell_file_types``. These prove each choice
changes what is registered -- through the real ``apply_shell_verb_settings``,
with only the registry writes faked, so no test touches the real registry.
"""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.settings import Settings
from quill.core.shell_file_types import allowed_extensions, narrow_verbs
from quill.core.shell_verbs import default_shell_verbs


def _registered(monkeypatch: pytest.MonkeyPatch, choice: str) -> dict[str, set[str]]:
    from quill.platform.windows import shell_integration

    installed: list[Any] = []
    monkeypatch.setattr(shell_integration, "winreg", object())
    monkeypatch.setattr(shell_integration, "remove_context_menu", lambda verbs=None: None)
    monkeypatch.setattr(shell_integration, "install_context_menu", installed.extend)
    settings = Settings(
        shell_integration_enabled=True, shell_verb_read=True, shell_file_types=choice
    )
    shell_integration.apply_shell_verb_settings(settings)
    return {verb.verb_id: set(verb.extensions) for verb in installed}


def test_images_only_takes_ocr_off_pdfs_and_drops_open(monkeypatch: pytest.MonkeyPatch) -> None:
    verbs = _registered(monkeypatch, "images")
    assert ".png" in verbs["ocr"]
    assert ".pdf" not in verbs["ocr"]
    assert "open" not in verbs  # Open in QUILL is for text documents only


def test_images_and_pdf_keeps_pdfs_but_not_text(monkeypatch: pytest.MonkeyPatch) -> None:
    verbs = _registered(monkeypatch, "images_pdf")
    assert ".pdf" in verbs["ocr"]
    assert ".txt" not in verbs.get("read", set())
    assert "open" not in verbs


def test_images_pdf_and_documents_offers_everything(monkeypatch: pytest.MonkeyPatch) -> None:
    verbs = _registered(monkeypatch, "images_pdf_docs")
    assert ".pdf" in verbs["ocr"]
    assert ".md" in verbs["open"]
    assert ".txt" in verbs["read"]


def test_media_belongs_to_convert_and_is_never_narrowed() -> None:
    convert = [v for v in default_shell_verbs() if v.verb_id == "convert"]
    assert narrow_verbs(convert, "images") == convert


def test_unknown_choice_means_every_kind() -> None:
    assert allowed_extensions("nonsense") == allowed_extensions("images_pdf_docs")
