"""GATE-CAPS (codex.md 10A.8): the tree is clean, and the scan sees what it must."""

from __future__ import annotations

from quill.tools import connection_caps_audit as audit


def test_the_tree_has_no_request_that_skips_the_capability_registry() -> None:
    assert [str(f) for f in audit.scan_tree()] == []


def test_every_capability_claim_names_its_source() -> None:
    assert audit.claim_findings() == []


def test_a_service_request_without_requires_is_found() -> None:
    source = (
        "class X:\n"
        "    def go(self):\n"
        "        self._service.ask('f', 'p', None, on_done=print, on_error=print)\n"
        "        self._service.ask('f', 'p', None, on_done=print, on_error=print,"
        " requires=('text',))\n"
    )
    findings = audit.scan_source(source, "quill/ui/example.py")
    assert [f.line for f in findings] == [3]


def test_an_engine_call_outside_a_checked_function_is_found() -> None:
    source = (
        "def bare(account):\n"
        "    return converse_with_chatgpt(account, 'hi', None, [])\n"
        "def checked(account):\n"
        "    require(record_for('chatgpt'), 'text')\n"
        "    return converse_with_chatgpt(account, 'hi', None, [])\n"
        "def free(client):\n"
        "    return client.ask('f', 'p', None)\n"
    )
    findings = audit.scan_source(source, "quill/apps/example.py")
    assert [f.line for f in findings] == [2, 7]


def test_the_service_methods_must_ask_request_allowed() -> None:
    source = "class AiService:\n    def ask(self):\n        return None\n"
    findings = audit.scan_source(source, audit.SERVICE_MODULE)
    assert [f.message for f in findings] == ["AiService.ask skips request_allowed"]


def test_the_command_line_passes_on_the_tree(capsys) -> None:
    assert audit.main([]) == 0
    assert "GATE-CAPS" in capsys.readouterr().out
