"""Save As Web Page, Word Document, Large Print and Braille-Ready Text (wordpress.md 17a.7)."""

from __future__ import annotations

from pathlib import Path

import pytest


def test_web_page_submits_where_you_say(fp, pub_dialogs, pub_host, tmp_path):
    target = tmp_path / "fair"
    pub_dialogs.answer("ask_text", "https://example.org/send").answer("save_as", target)

    fp.cmd_save_web_page()

    html = (tmp_path / "fair.html").read_text(encoding="utf-8")
    assert 'action="https://example.org/send"' in html
    assert '<label for="email">Email address <span class="required">(required)</span>' in html
    assert "<legend>How did you hear about us?</legend>" in html
    assert "Saved fair.html, a web page with 5 questions" in pub_host.said


def test_web_page_with_no_address_sends_nowhere(fp, pub_dialogs, pub_host, tmp_path):
    pub_dialogs.answer("ask_text", "").answer("save_as", tmp_path / "fair.html")

    fp.cmd_save_web_page()

    assert "action=" not in (tmp_path / "fair.html").read_text(encoding="utf-8")
    assert "sends its answers nowhere" in pub_host.said


def test_web_page_refuses_an_address_that_is_not_one(fp, pub_dialogs, pub_host, tmp_path):
    pub_dialogs.answer("ask_text", "example.org")

    fp.cmd_save_web_page()

    assert "not a web address" in pub_host.said
    assert not pub_dialogs.asked("save_as")


def test_web_page_cancelled_writes_nothing(fp, pub_dialogs, tmp_path):
    fp.cmd_save_web_page()

    assert not list(tmp_path.glob("*.html"))


def test_exports_work_in_safe_mode(fp, pub_dialogs, pub_host, tmp_path):
    pub_host.ai._safe_mode = True
    pub_dialogs.answer("ask_text", "").answer("save_as", tmp_path / "fair.html")

    fp.cmd_save_web_page()

    assert (tmp_path / "fair.html").exists()


@pytest.mark.parametrize(
    ("run", "large", "said"),
    [
        (lambda c: c.cmd_save_word(), False, "a Word form with 5 questions"),
        (lambda c: c.cmd_save_large_print(), True, "a large-print Word document, 18 point and up"),
    ],
)
def test_word_document_has_questions_boxes_and_lines(
    fp, pub_dialogs, pub_host, tmp_path, run, large, said
):
    import docx

    pub_dialogs.answer("save_as", tmp_path / "paper")

    run(fp)

    document = docx.Document(str(tmp_path / "paper.docx"))
    text = [p.text for p in document.paragraphs]
    assert "2. Email address (required)" in text
    assert "☐ A friend" in text
    assert any(t.startswith("____") for t in text)
    assert document.styles["Normal"].font.size.pt == (18 if large else 11)
    assert said in pub_host.said


def test_braille_ready_text_is_one_question_a_block(
    fp, pub_dialogs, pub_host, tmp_path, monkeypatch
):
    from quill.ui import forms_export_commands as fec

    monkeypatch.setattr(fec, "_braille_pack", lambda: False)
    pub_dialogs.answer("save_as", tmp_path / "fair.txt")

    fp.cmd_save_braille()

    text = (tmp_path / "fair.txt").read_bytes().decode("utf-8")
    assert (
        "4. How did you hear about us?\r\nChoose one.\r\n  a. A friend\r\n  b. Somewhere else"
        in text
    )
    assert max(len(line) for line in text.splitlines()) <= 40
    assert not pub_dialogs.asked("ask_choice")
    assert "braille-ready text with 5 questions" in pub_host.said


def test_braille_file_goes_through_quills_braille_output(
    fp, pub_dialogs, pub_host, tmp_path, monkeypatch
):
    from quill.core import braille_worker_client as worker
    from quill.ui import forms_export_commands as fec

    sent: list[tuple[str, str]] = []

    def translate(text: str, table: str = "", *, timeout: float = 0) -> str:
        sent.append((text, table))
        return ",SPR+ FAIR\n"

    monkeypatch.setattr(fec, "_braille_pack", lambda: True)
    monkeypatch.setattr(worker, "forward_translate", translate)
    pub_dialogs.answer("ask_choice", 1).answer("save_as", tmp_path / "fair")

    fp.cmd_save_braille()

    assert sent and sent[0][1] == "en-ueb-g2" and "Spring fair" in sent[0][0]
    assert (tmp_path / "fair.brf").read_bytes() == b",SPR+ FAIR\r\n"
    assert "a braille file in UEB contracted" in pub_host.said


def test_braille_translation_failure_saves_nothing(
    fp, pub_dialogs, pub_host, tmp_path, monkeypatch
):
    from quill.core import braille_worker_client as worker
    from quill.ui import forms_export_commands as fec

    def broken(*_a: object, **_k: object) -> str:
        raise worker.WorkerUnavailableError("no liblouis")

    monkeypatch.setattr(fec, "_braille_pack", lambda: True)
    monkeypatch.setattr(worker, "forward_translate", broken)
    pub_dialogs.answer("ask_choice", 1).answer("save_as", tmp_path / "fair.brf")

    fp.cmd_save_braille()

    assert not (tmp_path / "fair.brf").exists()
    assert "Nothing was saved." in pub_host.said


def test_export_outside_a_form_says_where_it_works(fp, pub_host, tmp_path):
    pub_host.path = Path(tmp_path / "letter.txt")

    fp.cmd_save_word()

    assert "works in a form document" in pub_host.said
