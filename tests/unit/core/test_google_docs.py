from __future__ import annotations

from quill.core.google_docs import (
    GoogleDocument,
    extract_google_doc_id,
    project_google_document,
)

_DOC_ID = "1A2b3C4d5E6f7G8h9I0jKlMnOpQrStUvWxYz"


def test_extract_id_from_edit_url() -> None:
    url = f"https://docs.google.com/document/d/{_DOC_ID}/edit?usp=sharing"
    assert extract_google_doc_id(url) == _DOC_ID


def test_extract_id_from_query_form() -> None:
    url = f"https://docs.google.com/open?id={_DOC_ID}"
    assert extract_google_doc_id(url) == _DOC_ID


def test_extract_id_from_bare_id() -> None:
    assert extract_google_doc_id(f"  {_DOC_ID}  ") == _DOC_ID


def test_extract_id_rejects_non_ids() -> None:
    assert extract_google_doc_id("") is None
    assert extract_google_doc_id("hello world") is None
    assert extract_google_doc_id("short") is None


def test_project_document_renders_headings_paragraphs_and_lists() -> None:
    payload = {
        "documentId": _DOC_ID,
        "title": "My Doc",
        "revisionId": "rev-7",
        "body": {
            "content": [
                {
                    "paragraph": {
                        "paragraphStyle": {"namedStyleType": "HEADING_1"},
                        "elements": [{"textRun": {"content": "Title Line\n"}}],
                    }
                },
                {
                    "paragraph": {
                        "elements": [{"textRun": {"content": "A plain paragraph.\n"}}],
                    }
                },
                {
                    "paragraph": {
                        "bullet": {"listId": "x"},
                        "elements": [{"textRun": {"content": "First item\n"}}],
                    }
                },
                {"table": {"rows": 2}},
            ]
        },
    }

    document = project_google_document(payload)

    assert isinstance(document, GoogleDocument)
    assert document.doc_id == _DOC_ID
    assert document.title == "My Doc"
    assert document.revision_id == "rev-7"
    assert document.body_text == "# Title Line\nA plain paragraph.\n- First item\n[table]"


def test_project_document_preserves_inline_objects_as_markers() -> None:
    payload = {
        "documentId": _DOC_ID,
        "title": "",
        "body": {
            "content": [
                {
                    "paragraph": {
                        "elements": [
                            {"textRun": {"content": "See "}},
                            {"inlineObjectElement": {"inlineObjectId": "img1"}},
                            {"textRun": {"content": " here\n"}},
                        ]
                    }
                }
            ]
        },
    }

    document = project_google_document(payload)

    assert document is not None
    assert document.title == "(untitled)"
    assert document.body_text == "See [inline object] here"


def test_project_document_rejects_malformed_payloads() -> None:
    assert project_google_document(None) is None
    assert project_google_document("not a dict") is None
    assert project_google_document({"title": "no id"}) is None
