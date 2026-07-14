"""Spell-check language chooser (Tools > Writing > Spell Check Language...).

English (en_US) ships inside pyenchant; other Hunspell languages download on
demand from QUILL's pinned, SHA-256-verified release asset (PRD 10.2.4) into the
managed dictionary folder, which the spell-check backend discovers via
``ENCHANT_CONFIG_DIR`` (see :mod:`quill.core.spellcheck`).

This module is the wx surface only; all acquisition/verification lives in
:mod:`quill.core.release_assets` and :mod:`quill.core.spellcheck`. The download
runs on a worker thread behind a cancelable percentage and is blocked in Safe
Mode by the core layer.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any

from quill.core import spellcheck
from quill.core.settings import save_settings


def open_spell_language_chooser(wx: Any, host: Any) -> None:
    """Show the language chooser and apply (or download then apply) the choice.

    *host* is the MainFrame: it supplies ``frame``, ``settings``,
    ``_show_modal_dialog``, ``_show_message_box``, ``_announce``, and
    ``_set_status``.
    """
    active = spellcheck.active_language()
    installed = spellcheck.installed_languages()
    installable = spellcheck.installable_languages()

    # Installed languages first (active marked), then the downloadable ones.
    entries: list[tuple[str, bool]] = [(lang, False) for lang in installed]
    entries += [(lang, True) for lang in installable]
    if not entries:
        host._show_message_box(
            "No spell-check languages are available.",
            "Spell Check Language",
            wx.ICON_INFORMATION | wx.OK,
        )
        return

    def _label(lang: str, needs_download: bool) -> str:
        name = spellcheck.language_display_name(lang)
        if needs_download:
            return f"{name} - download"
        return f"{name} - active" if lang == active else f"{name} - installed"

    labels = [_label(lang, dl) for lang, dl in entries]
    dialog = wx.SingleChoiceDialog(
        host.frame,
        "Choose the spell-check language. Items marked 'download' are fetched "
        "from QUILL's verified source the first time you pick them.",
        "Spell Check Language",
        labels,
    )
    try:
        dialog.SetSelection(next(i for i, (lang, _) in enumerate(entries) if lang == active))
    except StopIteration:
        pass
    try:
        if host._show_modal_dialog(dialog) != wx.ID_OK:
            return
        index = dialog.GetSelection()
    finally:
        dialog.Destroy()

    lang, needs_download = entries[index]
    if needs_download:
        _download_then_apply(wx, host, lang)
    else:
        _apply_language(host, lang)


def _apply_language(host: Any, lang: str) -> None:
    host.settings.spellcheck_language = lang
    save_settings(host.settings)
    spellcheck.set_active_language(lang)
    name = spellcheck.language_display_name(lang)
    host._set_status(f"Spell-check language set to {name}.")
    host._announce(f"Spell-check language set to {name}.")


def _download_then_apply(
    wx: Any, host: Any, lang: str, *, on_done: Callable[[bool], None] | None = None
) -> None:
    """Download *lang*'s dictionary and apply it. ``on_done(True)`` runs on
    success only (the hub's reopen-on-completion callback); a standalone caller
    with no hub to return to just omits it."""
    from quill.ui.ai_transcribe_dialog import AIProgressDialog

    name = spellcheck.language_display_name(lang)
    confirm = host._show_message_box(
        f"Download the {name} spell-check dictionary from QUILL's verified source? "
        "It is checksum-verified and used offline once installed.",
        "Spell Check Language",
        wx.ICON_QUESTION | wx.YES_NO,
    )
    if confirm != wx.YES:
        return

    cancel = threading.Event()
    progress = AIProgressDialog(
        host.frame,
        "Downloading Spell-Check Language",
        f"Preparing to download the {name} dictionary...",
        on_cancel=cancel.set,
        status_fn=host._set_status,
    )
    progress.show()
    host._announce(f"Downloading the {name} dictionary.")
    last_percent = {"value": -1}

    def _on_progress(fraction: float, message: str) -> None:
        percent = int(max(0.0, min(1.0, fraction)) * 100)
        if percent == last_percent["value"]:
            return  # throttle UI updates to whole-percent changes (#748)
        last_percent["value"] = percent
        progress.set_progress(percent, f"{message} {percent}%")

    def _run() -> None:
        try:
            spellcheck.install_language(lang, _on_progress, should_cancel=cancel.is_set)
        except Exception as exc:  # noqa: BLE001 - surface a clean message
            wx.CallAfter(progress.close)
            if cancel.is_set():
                wx.CallAfter(host._set_status, "Dictionary download cancelled.")
                wx.CallAfter(host._announce, "Dictionary download cancelled.")
            else:
                wx.CallAfter(host._set_status, f"Could not install the {name} dictionary: {exc}")
                wx.CallAfter(host._announce, f"Could not install the {name} dictionary. {exc}")
            return
        wx.CallAfter(progress.close)
        wx.CallAfter(_apply_language, host, lang)
        if on_done is not None:
            wx.CallAfter(on_done, True)

    threading.Thread(target=_run, daemon=True).start()  # GATE-40-OK: dictionary download worker.
