"""Behavioral tests for the free-first Import / Convert Document UI mixin.

Driven headless with a fake host (stub ``_wx``, synchronous task manager),
pinning the accessibility contract: results open as named tabs and are
announced, the Tier 1 -> 2 escalation always *asks* before OCR runs, a
missing engine offers the verified install instead of failing, and nothing
is ever uploaded (there is no code path that could).
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from quill.io.docconvert import (
    TIER_LOCAL_OCR,
    TIER_MARKITDOWN,
    ConversionOutcome,
    DocConvertCancelled,
)
from quill.ui.main_frame_docconvert import DocConvertMixin, _import_wildcard


class _FakeWx(SimpleNamespace):
    ID_OK = 1
    ID_CANCEL = 2
    YES = 5103
    NO = 5104
    CANCEL = 5101
    ICON_ERROR = 512
    ICON_INFORMATION = 2048
    ICON_WARNING = 256
    OK = 4
    YES_NO = 10
    YES_NO_CANCEL = 14
    FD_OPEN = 1
    FD_FILE_MUST_EXIST = 16


class _SyncTaskManager:
    def __init__(self) -> None:
        self.submitted: list[str] = []

    def submit(self, name, func, *, on_success=None, on_failure=None, on_progress=None, **kwargs):
        self.submitted.append(name)
        token = SimpleNamespace(is_cancelled=lambda: False)

        def _progress(payload):
            if on_progress is not None:
                on_progress("op", payload)

        try:
            result = func(progress_callback=_progress, cancellation_token=token)
        except BaseException as exc:  # noqa: BLE001 - mirrors QuillTaskManager
            if on_failure is not None:
                on_failure("op", exc)
            return SimpleNamespace(operation_id="op")
        if on_success is not None:
            on_success("op", result)
        return SimpleNamespace(operation_id="op")


class _Host(DocConvertMixin):
    def __init__(self, answers: list[int] | None = None) -> None:
        self._wx = _FakeWx()
        self.frame = object()
        self._task_manager = _SyncTaskManager()
        self.settings = SimpleNamespace(ocr_language="", tesseract_path="")
        self._answers = list(answers or [])
        self.tabs: list[tuple[int, str]] = []
        self.docs: list[str] = []
        self.statuses: list[str] = []
        self.announcements: list[str] = []
        self.message_boxes: list[str] = []
        self.html_pages: list[tuple[str, str]] = []

    def _show_message_box(self, message, _title, _style):
        self.message_boxes.append(message)
        return self._answers.pop(0) if self._answers else self._wx.YES

    def _create_document_tab(self, document, select=True):
        self.docs.append(document.text)
        return len(self.docs) - 1

    def _create_named_scratch_tab(self, title, text):
        self.tabs.append((title, text))

    def _set_tab_page_text(self, index, title):
        self.tabs.append((index, title))

    def _set_status(self, message):
        self.statuses.append(str(message))

    def _announce(self, message):
        self.announcements.append(message)

    def _html_info(self, title, markdown):
        self.html_pages.append((title, markdown))


def _outcome(**kwargs) -> ConversionOutcome:
    base = {
        "text": "# Converted\n",
        "tier": TIER_MARKITDOWN,
        "source": Path("report.docx"),
    }
    base.update(kwargs)
    return ConversionOutcome(**base)


def test_wildcard_lists_documents_images_and_pdf() -> None:
    wildcard = _import_wildcard()
    assert "*.docx" in wildcard
    assert "*.pdf" in wildcard
    assert "*.png" in wildcard


def test_tier1_result_opens_tab_and_announces_no_upload(monkeypatch) -> None:
    host = _Host()
    import quill.io.docconvert as docconvert

    monkeypatch.setattr(docconvert, "convert_document", lambda path, **kw: _outcome())
    host._docconvert_start(Path("report.docx"))
    assert host.docs == ["# Converted\n"]
    assert host.tabs[0][1] == "report (converted)"
    assert any("Nothing was uploaded" in item for item in host.announcements)


def test_scanned_pdf_prompts_before_ocr_and_yes_runs_it(monkeypatch) -> None:
    host = _Host(answers=[_FakeWx.YES])
    import quill.io.docconvert as docconvert
    import quill.io.tesseract_ocr as tesseract_ocr

    monkeypatch.setattr(
        docconvert,
        "convert_document",
        lambda path, **kw: _outcome(text="", offer_local_ocr=True, source=Path("scan.pdf")),
    )
    monkeypatch.setattr(tesseract_ocr, "tesseract_available", lambda override=None: True)
    monkeypatch.setattr(
        docconvert,
        "convert_with_local_ocr",
        lambda path, **kw: _outcome(
            text="<!-- Page 1 -->\n\nRescued text.\n",
            tier=TIER_LOCAL_OCR,
            source=Path("scan.pdf"),
            page_count=3,
            mean_confidence=88.0,
        ),
    )
    host._docconvert_start(Path("scan.pdf"))
    # The escalation prompt ran, stayed local, and said so.
    assert any("does not upload anything" in box for box in host.message_boxes)
    assert host._task_manager.submitted == ["docconvert-import", "docconvert-local-ocr"]
    assert any("on-device OCR" in item for item in host.announcements)
    assert any("Confidence 88" in item for item in host.announcements)


def test_escalation_no_opens_empty_result_anyway(monkeypatch) -> None:
    host = _Host(answers=[_FakeWx.NO])
    import quill.io.docconvert as docconvert

    monkeypatch.setattr(
        docconvert,
        "convert_document",
        lambda path, **kw: _outcome(text="", offer_local_ocr=True, source=Path("scan.pdf")),
    )
    host._docconvert_start(Path("scan.pdf"))
    assert host.docs == [""]
    assert host._task_manager.submitted == ["docconvert-import"]


def test_escalation_cancel_imports_nothing(monkeypatch) -> None:
    host = _Host(answers=[_FakeWx.CANCEL])
    import quill.io.docconvert as docconvert

    monkeypatch.setattr(
        docconvert,
        "convert_document",
        lambda path, **kw: _outcome(text="", offer_local_ocr=True, source=Path("scan.pdf")),
    )
    host._docconvert_start(Path("scan.pdf"))
    assert host.docs == []
    assert any("No result was imported" in status for status in host.statuses)


def test_missing_engine_offers_verified_install(monkeypatch) -> None:
    host = _Host(answers=[_FakeWx.YES, _FakeWx.NO])  # yes to install offer, no at consent
    import quill.io.tesseract_ocr as tesseract_ocr

    monkeypatch.setattr(tesseract_ocr, "tesseract_available", lambda override=None: False)
    host._docconvert_run_local_ocr(Path("scan.pdf"))
    assert any("not installed yet" in box for box in host.message_boxes)
    # Install consent was shown next (and declined) — never a silent download.
    assert any("verify it" in box for box in host.message_boxes)
    assert host._task_manager.submitted == []


def test_install_flow_downloads_then_launches_visibly(monkeypatch, tmp_path) -> None:
    host = _Host(answers=[_FakeWx.YES])
    import quill.core.tesseract_install as tesseract_install

    installer = tmp_path / "setup.exe"
    installer.write_bytes(b"x")
    monkeypatch.setattr(
        tesseract_install, "download_tesseract_installer", lambda progress_fn=None: installer
    )
    launched: list[Path] = []
    monkeypatch.setattr(
        tesseract_install, "launch_tesseract_installer", lambda path: launched.append(path)
    )
    host.install_local_ocr_engine()
    assert launched == [installer]
    assert any("installer is open" in item for item in host.announcements)


def test_cancelled_conversion_is_quiet_not_an_error() -> None:
    host = _Host()
    host._docconvert_failed(Path("scan.pdf"), DocConvertCancelled("cancelled"))
    assert host.message_boxes == []
    assert any("cancelled" in status.lower() for status in host.statuses)


def test_weak_local_result_offers_consented_cloud_escalation(monkeypatch, tmp_path) -> None:
    # Weak Tier-2 outcome + configured cloud -> the §11.4 Tier 2->3 prompt,
    # then the §15.1 upload consent; declining consent uploads nothing.
    host = _Host(answers=[_FakeWx.YES, _FakeWx.NO])  # yes to escalate, no at consent
    import quill.core.datalab_ocr as datalab_ocr

    monkeypatch.setattr(datalab_ocr, "datalab_configured", lambda settings: True)
    weak = _outcome(
        text="noisy\n",
        tier=TIER_LOCAL_OCR,
        source=tmp_path / "scan.pdf",
        mean_confidence=30.0,
    )
    host._docconvert_open(weak.source, weak)
    boxes = " || ".join(host.message_boxes)
    assert "may cost money" in boxes  # the escalation names cost + upload
    assert "send this document to Datalab" in boxes  # the §15.1 consent ran
    assert host._task_manager.submitted == []  # declined consent -> no upload
    assert any("nothing was uploaded" in status for status in host.statuses)


def test_cloud_consent_accepted_runs_the_cloud_task(monkeypatch, tmp_path) -> None:
    host = _Host(answers=[_FakeWx.YES])  # consent yes
    import quill.core.datalab_ocr as datalab_ocr
    import quill.io.docconvert as docconvert

    monkeypatch.setattr(datalab_ocr, "datalab_configured", lambda settings: True)
    monkeypatch.setattr(
        docconvert,
        "convert_with_cloud_ocr",
        lambda path, **kw: _outcome(text="# Cloud\n", tier="cloud-ocr", source=path, page_count=4),
    )
    host._docconvert_run_cloud(tmp_path / "scan.pdf")
    assert host._task_manager.submitted == ["docconvert-cloud-ocr"]
    assert any("Datalab cloud OCR" in item for item in host.announcements)


def test_sensitive_filename_adds_the_extra_warning(monkeypatch, tmp_path) -> None:
    host = _Host(answers=[_FakeWx.NO])
    host._docconvert_run_cloud(tmp_path / "tax-return-2025.pdf")
    assert any("CAUTION" in box for box in host.message_boxes)


def test_review_last_ocr_without_a_conversion_is_quiet() -> None:
    host = _Host()
    host.review_last_ocr_result()
    assert host.tabs == []
    assert any("No conversion to review" in status for status in host.statuses)


def test_review_last_ocr_lists_flagged_lines(tmp_path) -> None:
    host = _Host()
    host._docconvert_last_outcome = _outcome(
        text="text",
        tier=TIER_LOCAL_OCR,
        source=tmp_path / "scan.pdf",
        page_count=2,
        mean_confidence=55.0,
        low_confidence=("Page 2: [40%] blurry words",),
    )
    host.review_last_ocr_result()
    title, body = host.tabs[0]
    assert "OCR Review" in title
    assert "Page 2: [40%] blurry words" in body
    assert "on-device OCR" in body
    assert any("1 lines flagged" in item for item in host.announcements)


def test_delete_ocr_temp_files_reports_when_nothing_to_do(monkeypatch, tmp_path) -> None:
    host = _Host()
    monkeypatch.setattr("quill.core.paths.app_data_dir", lambda: tmp_path)
    host.delete_ocr_temp_files()
    assert any("No OCR temporary files" in status for status in host.statuses)


def test_delete_ocr_temp_files_removes_job_leftovers(monkeypatch, tmp_path) -> None:
    host = _Host()
    monkeypatch.setattr("quill.core.paths.app_data_dir", lambda: tmp_path)
    job = tmp_path / "ocr_jobs" / "job-1"
    job.mkdir(parents=True)
    (job / "page.png").write_bytes(b"x")
    host.delete_ocr_temp_files()
    assert not job.exists()
    assert any("Deleted 1" in item for item in host.announcements)


def test_services_overview_names_engine_status(monkeypatch) -> None:
    host = _Host()
    import quill.io.tesseract_ocr as tesseract_ocr

    monkeypatch.setattr(tesseract_ocr, "discover_tesseract_executable", lambda override=None: None)
    host.show_ocr_services_overview()
    title, markdown = host.html_pages[0]
    assert "OCR and Document Conversion Services" in title
    assert "Free first, local first" in markdown
    assert "not installed" in markdown
