"""Free-first document conversion UI (MainFrame mixin).

Wires the supported **Import / Convert Document** tool over
:mod:`quill.io.docconvert` — the PRD's free-first routing (Tier 1 the file's
own text: MarkItDown for Office/HTML/EPUB where it can run and QUILL's own
readers (quill.io.office_text) where it cannot, QUILL's PDF reader for PDFs; Tier 2
local Tesseract OCR, or Windows OCR when Tesseract is not installed), with the
accessible escalation prompt between
them. Conversion runs on the background task pool; QUILL never opens an empty
or garbled result silently, and never runs OCR without asking.

Also hosts the two supporting commands:

* **Install Local OCR Engine (Tesseract)...** — downloads the SHA-256-pinned
  official installer from QUILL's assets release and launches it visibly
  (:mod:`quill.core.tesseract_install`).
* **OCR and Conversion Services...** — the customer-facing services overview
  page (what each tier does, what it costs — nothing — and what stays on your
  machine — everything).

Wiring expectations from MainFrame: ``_wx``, ``frame``, ``_task_manager``,
``_show_modal_dialog``, ``_show_message_box``, ``_create_document_tab``,
``_set_tab_page_text``, ``_set_status``, ``_announce``, ``_html_info``,
``settings``.
"""

from __future__ import annotations

from pathlib import Path

from quill.core.docconvert_services import SERVICES_OVERVIEW_MARKDOWN
from quill.core.document import Document
from quill.core.import_convert import (
    CANCELLED_SENTENCE,
    IMPORT_TITLE,
    converted_name,
    failed_sentence,
    opened_sentence,
    scanned_import_question,
)
from quill.core.import_convert import import_wildcard as _import_wildcard

# The file list and every sentence below are shared with QUILL Lite's File >
# Import / Convert Document (quill/core/import_convert.py, 2026-10-17): one
# wording, so the two editors cannot describe one conversion two ways.


class DocConvertMixin:
    """``file.import_convert`` and the OCR service commands."""

    def import_convert_document(self) -> None:
        """Pick a document and route it through the free-first conversion tiers."""
        wx = self._wx
        dialog = wx.FileDialog(
            self.frame,
            IMPORT_TITLE,
            wildcard=_import_wildcard(),
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        )
        try:
            if self._show_modal_dialog(dialog, IMPORT_TITLE) != wx.ID_OK:
                self._set_status("Import / Convert Document cancelled")
                return
            source = Path(dialog.GetPath())
        finally:
            dialog.Destroy()
        self._docconvert_start(source)

    # ------------------------------------------------------------------ tiers

    def _docconvert_start(self, source: Path) -> None:
        from quill.io.docconvert import convert_document

        language = self._docconvert_language()
        self._set_status(f"Converting {source.name} with the free local converter...")

        def _run(progress_callback, **_kw):
            return convert_document(
                source,
                language=language,
                on_progress=lambda fraction, message: progress_callback(message),
            )

        self._task_manager.submit(
            name="docconvert-import",
            func=_run,
            on_success=lambda _op, outcome: self._docconvert_finished(source, outcome),
            on_failure=lambda _op, error: self._docconvert_failed(source, error),
            on_progress=lambda _op, message: self._set_status(str(message)),
        )

    def _docconvert_finished(self, source: Path, outcome) -> None:
        wx = self._wx
        if outcome.offer_local_ocr:
            # PRD §11.4 Tier 1 -> 2 escalation prompt (stays free and local).
            choice = self._show_message_box(
                scanned_import_question(source.name),
                IMPORT_TITLE,
                wx.ICON_INFORMATION | wx.YES_NO | wx.CANCEL,
            )
            if choice == wx.YES:
                self._docconvert_run_local_ocr(source)
                return
            if choice != wx.NO:
                self._set_status(CANCELLED_SENTENCE)
                return
        self._docconvert_open(source, outcome)

    def _docconvert_run_local_ocr(self, source: Path) -> None:
        from quill.io.docconvert_windows import windows_ocr_available
        from quill.io.tesseract_ocr import tesseract_available

        if not tesseract_available(self._docconvert_tesseract_override()):
            if windows_ocr_available():
                # Windows OCR is already on this computer: no download, no
                # question. Tesseract stays the first choice when installed,
                # because it reports a confidence per line (2026-10-15).
                self._docconvert_run_windows_ocr(source)
                return
            wx = self._wx
            wants_install = self._show_message_box(
                (
                    "The free local OCR engine (Tesseract) is not installed yet.\n\n"
                    "Install it now? QUILL downloads the official installer "
                    "(about 48 MB), verifies it, and opens it for you to complete. "
                    "Then run Import / Convert Document again."
                ),
                "Local OCR Engine",
                wx.ICON_INFORMATION | wx.YES_NO,
            )
            if wants_install == wx.YES:
                self.install_local_ocr_engine()
            elif self._docconvert_cloud_available():
                # Free-first still holds: the cloud is only offered once the
                # free path was declined, and it remains consent-gated.
                self._docconvert_offer_cloud(source)
            else:
                self._set_status("Local OCR is not installed; conversion stopped")
            return
        from quill.io.docconvert import convert_with_local_ocr

        language = self._docconvert_language()
        self._set_status(f"Running free on-device OCR on {source.name}...")

        def _run(progress_callback, cancellation_token, **_kw):
            return convert_with_local_ocr(
                source,
                language=language,
                on_progress=lambda fraction, message: progress_callback(message),
                cancel_requested=cancellation_token.is_cancelled,
            )

        self._task_manager.submit(
            name="docconvert-local-ocr",
            func=_run,
            on_success=lambda _op, outcome: self._docconvert_open(source, outcome),
            on_failure=lambda _op, error: self._docconvert_failed(source, error),
            on_progress=lambda _op, message: self._set_status(str(message)),
        )

    # ---------------------------------------------------------------- results

    def _docconvert_open(self, source: Path, outcome) -> None:
        from quill.io.docconvert import TIER_LOCAL_OCR

        self._docconvert_last_outcome = outcome
        # modified=True: the conversion/OCR result exists nowhere else, so the
        # close/exit save prompts must protect it (#790 review) — closing a
        # pathless, "unmodified" tab would silently discard the whole result.
        index = self._create_document_tab(
            Document(text=outcome.text, path=None, modified=True),
            select=True,
        )
        self._set_tab_page_text(index, converted_name(source.stem))
        self._announce(opened_sentence(source.name, outcome))
        for warning in outcome.warnings:
            self._set_status(str(warning))
        if outcome.tier == TIER_LOCAL_OCR and outcome.looks_weak:
            self._docconvert_offer_cloud(source)

    # ----------------------------------------------------------- cloud tier

    def _docconvert_cloud_available(self) -> bool:
        from quill.core.datalab_ocr import datalab_configured

        return datalab_configured(self.settings)

    def _docconvert_offer_cloud(self, source: Path) -> None:
        """PRD §11.4 Tier 2 -> 3 escalation — the only prompt that mentions
        cost or upload, shown only when the cloud service is configured."""
        if not self._docconvert_cloud_available():
            return
        wx = self._wx
        choice = self._show_message_box(
            (
                "On-device OCR finished, but the result looks low-quality or the "
                "layout is complex. For higher accuracy you can convert it with "
                "Datalab cloud OCR. This uploads the file to a cloud service and "
                "may cost money.\n\n"
                "Yes: convert with cloud OCR.  No: keep the local result."
            ),
            "Convert with Cloud OCR?",
            wx.ICON_INFORMATION | wx.YES_NO,
        )
        if choice == wx.YES:
            self._docconvert_run_cloud(source)

    def _docconvert_run_cloud(self, source: Path) -> None:
        """Consent-gated Tier 3: never uploads without the §15.1 dialog."""
        wx = self._wx
        from quill.core.datalab_ocr import looks_sensitive

        consent = (
            "QUILL will send this document to Datalab for OCR and document "
            "conversion. Only continue if you are allowed to upload this file "
            "to that service. Consider whether the document contains private, "
            "medical, legal, educational, financial, employment, or "
            "confidential information.\n\n"
            "Datalab says conversion results are deleted from its servers about "
            "one hour after processing; QUILL retrieves the result promptly and "
            "keeps it only in the opened document."
        )
        if looks_sensitive(source):
            consent = (
                "CAUTION: this file's name suggests it may contain sensitive "
                "personal information.\n\n" + consent
            )
        proceed = self._show_message_box(
            consent + "\n\nSend the document to Datalab now?",
            "Cloud Upload Consent",
            wx.ICON_WARNING | wx.YES_NO,
        )
        if proceed != wx.YES:
            self._set_status("Cloud conversion cancelled; nothing was uploaded")
            return
        from quill.io.docconvert import convert_with_cloud_ocr

        settings = self.settings
        self._set_status(f"Sending {source.name} to Datalab (with your consent)...")

        def _run(progress_callback, cancellation_token, **_kw):
            return convert_with_cloud_ocr(
                source,
                endpoint=str(getattr(settings, "datalab_endpoint", "") or ""),
                mode=str(getattr(settings, "datalab_mode", "balanced") or "balanced"),
                output_format=str(getattr(settings, "datalab_output", "markdown") or "markdown"),
                paginate=bool(getattr(settings, "datalab_paginate", True)),
                on_progress=lambda fraction, message: progress_callback(message),
                cancel_requested=cancellation_token.is_cancelled,
            )

        self._task_manager.submit(
            name="docconvert-cloud-ocr",
            func=_run,
            on_success=lambda _op, outcome: self._docconvert_open(source, outcome),
            on_failure=lambda _op, error: self._docconvert_failed(source, error),
            on_progress=lambda _op, message: self._set_status(str(message)),
        )

    # ---------------------------------------------------------- review mode

    def review_last_ocr_result(self) -> None:
        """OCR Review Mode: a spoken checklist over the last conversion.

        Opens a named tab with the conversion's provenance, its confidence,
        and every low-confidence line pre-formatted as "Page N: [NN%] text" —
        so a screen-reader user can walk exactly the trouble spots (search the
        page marker in the converted document to jump there) instead of
        re-proofreading everything.
        """
        outcome = getattr(self, "_docconvert_last_outcome", None)
        if outcome is None:
            self._set_status("No conversion to review yet. Run Import / Convert Document first.")
            return
        from quill.io.docconvert import (
            TIER_CLOUD_OCR,
            TIER_LOCAL_OCR,
            TIER_MARKITDOWN,
            TIER_OWN_READER,
            TIER_PDF_TEXT,
            TIER_WINDOWS_OCR,
        )

        tier_labels = {
            TIER_MARKITDOWN: "Free local converter (MarkItDown) - no OCR was needed",
            TIER_OWN_READER: f"{outcome.reader or 'QUILL'} - no OCR was needed",
            TIER_PDF_TEXT: "The PDF's own text (QUILL's PDF reader) - no OCR was needed",
            TIER_LOCAL_OCR: "Free on-device OCR (Tesseract)",
            TIER_WINDOWS_OCR: "Free on-device OCR (Windows OCR) - no confidence is reported",
            TIER_CLOUD_OCR: "Datalab Chandra cloud OCR (consented upload)",
        }
        lines = [
            "OCR Review",
            "",
            f"Source: {outcome.source.name}",
            f"Converted with: {tier_labels.get(outcome.tier, outcome.tier)}",
        ]
        if outcome.page_count:
            lines.append(f"Pages: {outcome.page_count}")
        if outcome.units:
            lines.append(f"Contents: {outcome.units}")
        if outcome.mean_confidence >= 0.0:
            lines.append(f"Mean recognition confidence: {outcome.mean_confidence:.0f} out of 100")
        for warning in outcome.warnings:
            lines.append(f"Warning: {warning}")
        lines.append("")
        if outcome.low_confidence:
            lines.extend([
                f"Lines needing review: {len(outcome.low_confidence)}",
                "Search the converted document for the page marker "
                "(for example '<!-- Page 3 -->') to jump to a flagged line.",
                "",
            ])
            lines.extend(outcome.low_confidence)
        elif outcome.tier == TIER_LOCAL_OCR:
            lines.append("No low-confidence lines were flagged. The recognition looks clean.")
        else:
            lines.append(
                "This conversion carries no per-line confidence data; review the "
                "opened document normally."
            )
        self._create_named_scratch_tab(f"OCR Review - {outcome.source.name}", "\n".join(lines))
        flagged = len(outcome.low_confidence)
        self._announce(
            f"OCR review for {outcome.source.name}: {flagged} lines flagged for review."
            if flagged
            else f"OCR review for {outcome.source.name}: nothing flagged."
        )

    # ------------------------------------------------------------ temp files

    def delete_ocr_temp_files(self) -> None:
        """Delete leftover OCR job files (PRD §13.5) and say what was removed.

        The local tiers already clean up after themselves (per-run temporary
        directories); this clears anything left in the app-data ocr_jobs
        folder, e.g. after a crash mid-conversion.
        """
        import shutil

        from quill.core.paths import app_data_dir

        jobs_dir = app_data_dir() / "ocr_jobs"
        if not jobs_dir.is_dir() or not any(jobs_dir.iterdir()):
            self._set_status("No OCR temporary files to delete")
            return
        entries = list(jobs_dir.iterdir())
        removed = 0
        for entry in entries:
            try:
                if entry.is_dir():
                    shutil.rmtree(entry)
                else:
                    entry.unlink()
                removed += 1
            except OSError:
                continue
        self._announce(f"Deleted {removed} OCR temporary item(s).")
        self._set_status("OCR temporary files deleted")

    def _docconvert_failed(self, source: Path, error: BaseException) -> None:
        from quill.io.docconvert import DocConvertCancelled

        if isinstance(error, DocConvertCancelled):
            self._set_status(CANCELLED_SENTENCE)
            return
        wx = self._wx
        self._set_status("Conversion failed")
        self._show_message_box(
            failed_sentence(source.name, error),
            IMPORT_TITLE,
            wx.ICON_ERROR | wx.OK,
        )

    # ---------------------------------------------------------------- install

    def install_local_ocr_engine(self) -> None:
        """Download the pinned Tesseract installer and open it (never silent)."""
        wx = self._wx
        from quill.core.tesseract_install import (
            TESSERACT_DOWNLOAD_BYTES,
            TESSERACT_VERSION,
            download_tesseract_installer,
            launch_tesseract_installer,
        )

        size_mb = TESSERACT_DOWNLOAD_BYTES / (1024 * 1024)
        proceed = self._show_message_box(
            (
                f"QUILL will download the official Tesseract OCR installer "
                f"(version {TESSERACT_VERSION}, about {size_mb:.0f} MB), verify it "
                "byte-for-byte, and then open it for you to complete.\n\n"
                "Tesseract is free, runs entirely on this computer, and never "
                "uploads your documents. Continue?"
            ),
            "Install Local OCR Engine",
            wx.ICON_INFORMATION | wx.YES_NO,
        )
        if proceed != wx.YES:
            self._set_status("Local OCR install cancelled")
            return
        self._set_status("Downloading the local OCR engine...")

        def _run(progress_callback, **_kw):
            return download_tesseract_installer(
                progress_fn=lambda fraction, message: progress_callback(message)
            )

        def _on_success(_op, installer: Path) -> None:
            try:
                launch_tesseract_installer(installer)
            except Exception as error:  # noqa: BLE001 - surfaced to the user
                self._ocr_install_failed(error)
                return
            self._announce(
                "The verified Tesseract installer is open. Complete it, then use "
                "Import / Convert Document — QUILL will find the engine automatically."
            )
            self._set_status("Tesseract installer launched")

        self._task_manager.submit(
            name="tesseract-install-download",
            func=_run,
            on_success=_on_success,
            on_failure=lambda _op, error: self._ocr_install_failed(error),
            on_progress=lambda _op, message: self._set_status(str(message)),
        )

    def _ocr_install_failed(self, error: BaseException) -> None:
        """Report an OCR-engine install/launch failure as what it is.

        Routing this through _docconvert_failed produced a misleading "could
        not convert tesseract-installer" message (#790 review) — this is an
        install problem, not a conversion problem.
        """
        wx = self._wx
        self._set_status("Local OCR install failed")
        self._show_message_box(
            f"QUILL could not download or launch the Tesseract OCR installer.\n\n{error}",
            "Install Local OCR Engine",
            wx.ICON_ERROR | wx.OK,
        )

    # ------------------------------------------------------------------ info

    def show_ocr_services_overview(self) -> None:
        """Open the customer-facing OCR and conversion services page."""
        from quill.core.datalab_ocr import datalab_configured
        from quill.io.tesseract_ocr import discover_tesseract_executable

        engine = discover_tesseract_executable(self._docconvert_tesseract_override())
        local_status = (
            f"**Local OCR engine status:** installed ({engine})."
            if engine is not None
            else "**Local OCR engine status:** not installed — free download available."
        )
        if datalab_configured(self.settings):
            cloud_status = "**Datalab cloud OCR status:** Ready (enabled, API key present)."
        elif bool(getattr(self.settings, "datalab_enabled", False)):
            cloud_status = (
                "**Datalab cloud OCR status:** Needs API key — add one in AI Hub > Services."
            )
        else:
            cloud_status = "**Datalab cloud OCR status:** Not configured (optional)."
        self._html_info(
            "OCR and Document Conversion Services",
            SERVICES_OVERVIEW_MARKDOWN + "\n\n" + local_status + "\n\n" + cloud_status + "\n",
        )

    # -------------------------------------------------------------- settings

    def _docconvert_language(self) -> str:
        value = str(getattr(self.settings, "ocr_language", "") or "").strip()
        return value or "eng"

    def _docconvert_tesseract_override(self) -> str | None:
        value = str(getattr(self.settings, "tesseract_path", "") or "").strip()
        return value or None
