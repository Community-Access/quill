"""Free-first document conversion UI (MainFrame mixin).

Wires the supported **Import / Convert Document** tool over
:mod:`quill.io.docconvert` — the PRD's free-first routing (Tier 1 MarkItDown,
Tier 2 local Tesseract OCR), with the accessible escalation prompt between
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

from quill.core.document import Document


def _import_wildcard() -> str:
    from quill.io.docconvert import (
        BORN_DIGITAL_EXTENSIONS,
        IMAGE_EXTENSIONS,
        PDF_EXTENSION,
    )

    def _mask(extensions: frozenset[str] | set[str]) -> str:
        return ";".join(f"*{ext}" for ext in sorted(extensions))

    everything = _mask(BORN_DIGITAL_EXTENSIONS | IMAGE_EXTENSIONS | {PDF_EXTENSION})
    return (
        f"All convertible documents ({everything})|{everything}"
        f"|Documents ({_mask(BORN_DIGITAL_EXTENSIONS | {PDF_EXTENSION})})"
        f"|{_mask(BORN_DIGITAL_EXTENSIONS | {PDF_EXTENSION})}"
        f"|Images ({_mask(IMAGE_EXTENSIONS)})|{_mask(IMAGE_EXTENSIONS)}"
        "|All files (*.*)|*.*"
    )


SERVICES_OVERVIEW_MARKDOWN = """# OCR and Document Conversion Services

QUILL's Import / Convert Document tool turns documents that are hard to read
— scanned PDFs, photos of pages, locked-down Office files — into editable
text. It always tries the **free, private, on-device** services first, and it
never uploads anything.

## Free Local Converter (MarkItDown) — installed with QUILL

- **What it does:** reads the text that born-digital files already contain —
  Word, PowerPoint, Excel, HTML, EPUB, and PDFs that carry a text layer — and
  opens it as clean, editable Markdown.
- **Best for:** files that were *made* on a computer.
- **Local or cloud?** Local. Nothing is uploaded. No account, no API key.
- **Cost:** free, always.
- **Limits:** it is not OCR — a scanned or photographed page comes back
  empty. When that happens QUILL offers the next service automatically.

## Local OCR Engine (Tesseract) — free download, runs on your computer

- **What it does:** real optical character recognition for scanned PDFs,
  photos, and images, running entirely on your machine (CPU-only — no
  special hardware).
- **Best for:** scanned letters, handouts, forms, and photographed pages.
- **Local or cloud?** Local. Your document never leaves this computer.
- **Cost:** free. The engine is a one-time download of about 48 MB.
- **Setup:** Tools > OCR and Document Conversion > Install Local OCR Engine.
  QUILL downloads the official installer, verifies it byte-for-byte, and
  opens it for you to complete. If Tesseract is already installed on this
  computer, QUILL finds and uses it — no download needed.
- **Honesty note:** on-device OCR is very good on clean scans and weaker on
  complex tables, handwriting, and poor photocopies. QUILL tells you when a
  result's confidence is low so you know to review it.

## Datalab Chandra OCR Service — cloud, optional, consent-gated

- **What it does:** the accuracy escalation for the hardest documents —
  complex tables, forms, handwriting, math, dense multi-column layouts, and
  poor scans. Returns clean Markdown (or HTML/JSON) with strong layout
  understanding.
- **Best for:** documents the free local tiers could not rescue well. QUILL
  offers it only after local OCR comes back weak — never as the first stop.
- **Local or cloud?** Cloud. Converting a document sends the file to
  Datalab. QUILL asks for your explicit consent before every single upload,
  and warns again when a filename suggests sensitive content. Datalab states
  that results are deleted from its servers about an hour after processing;
  QUILL retrieves promptly and keeps the result only in the opened document.
- **Cost:** paid, per page, on your own Datalab account (bring your own API
  key; new accounts include a monthly free allowance). QUILL never sees your
  billing — check Datalab's pricing page for current rates.
- **Setup:** AI Hub > Services — enable the service, paste your API key
  (stored in the Windows credential vault, never in settings files), choose
  a default mode, and press Test Connection.

## The one rule

Free first, local first, and nothing is ever uploaded without asking you.
The cloud tier exists for the documents that genuinely need it — and it
always asks first.
"""


class DocConvertMixin:
    """``file.import_convert`` and the OCR service commands."""

    def import_convert_document(self) -> None:
        """Pick a document and route it through the free-first conversion tiers."""
        wx = self._wx
        dialog = wx.FileDialog(
            self.frame,
            "Import / Convert Document",
            wildcard=_import_wildcard(),
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        )
        try:
            if self._show_modal_dialog(dialog, "Import / Convert Document") != wx.ID_OK:
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
                (
                    f"QUILL could not find readable text in {source.name}. "
                    "It looks scanned or image-based.\n\n"
                    "Run free on-device OCR (local Tesseract)? This stays on "
                    "your computer and does not upload anything.\n\n"
                    "Yes: run local OCR now.  No: open the empty result anyway.  "
                    "Cancel: stop."
                ),
                "Import / Convert Document",
                wx.ICON_INFORMATION | wx.YES_NO | wx.CANCEL,
            )
            if choice == wx.YES:
                self._docconvert_run_local_ocr(source)
                return
            if choice != wx.NO:
                self._set_status("Conversion cancelled. No result was imported.")
                return
        self._docconvert_open(source, outcome)

    def _docconvert_run_local_ocr(self, source: Path) -> None:
        from quill.io.tesseract_ocr import tesseract_available

        if not tesseract_available(self._docconvert_tesseract_override()):
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
        from quill.io.docconvert import TIER_CLOUD_OCR, TIER_LOCAL_OCR

        self._docconvert_last_outcome = outcome
        # modified=True: the conversion/OCR result exists nowhere else, so the
        # close/exit save prompts must protect it (#790 review) — closing a
        # pathless, "unmodified" tab would silently discard the whole result.
        index = self._create_document_tab(
            Document(text=outcome.text, path=None, modified=True),
            select=True,
        )
        self._set_tab_page_text(index, f"{source.stem} (converted)")
        if outcome.tier == TIER_CLOUD_OCR:
            pages = f" {outcome.page_count} pages." if outcome.page_count > 1 else ""
            self._announce(
                f"Opened {source.name} from Datalab cloud OCR.{pages} "
                "The result was retrieved and is only stored in this document."
            )
        elif outcome.tier == TIER_LOCAL_OCR:
            confidence = (
                f" Confidence {outcome.mean_confidence:.0f} out of 100."
                if outcome.mean_confidence >= 0.0
                else ""
            )
            pages = f" {outcome.page_count} pages." if outcome.page_count > 1 else ""
            self._announce(f"Opened {source.name} from free on-device OCR.{pages}{confidence}")
        else:
            self._announce(
                f"Opened {source.name} as editable text using the free local converter. "
                "Nothing was uploaded."
            )
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
        from quill.io.docconvert import TIER_CLOUD_OCR, TIER_LOCAL_OCR, TIER_MARKITDOWN

        tier_labels = {
            TIER_MARKITDOWN: "Free local converter (MarkItDown) - no OCR was needed",
            TIER_LOCAL_OCR: "Free on-device OCR (Tesseract)",
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
            self._set_status("Conversion cancelled. No result was imported.")
            return
        wx = self._wx
        self._set_status("Conversion failed")
        self._show_message_box(
            f"QUILL could not convert {source.name}.\n\n{error}",
            "Import / Convert Document",
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
