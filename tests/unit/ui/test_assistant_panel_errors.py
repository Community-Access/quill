from __future__ import annotations

from quill.ui.assistant_panel import classify_assistant_error


def test_classify_assistant_error_native_loader_failure() -> None:
    message, disable_chat = classify_assistant_error(
        "llama-cpp-python failed to load native code on this machine "
        "(Windows error 0xc000001d). Install a CPU-compatible build or disable AI."
    )

    # Issue #137: the user-facing message must be plain-language and
    # platform-neutral — no hex codes, no "Windows", no library jargon — even
    # though the raw error (the trigger) contains those technical details.
    assert "0xc000001d" not in message
    assert "Windows" not in message
    assert "llama" not in message.lower()
    assert "turn AI off" in message
    assert disable_chat is True


def test_classify_assistant_error_generic() -> None:
    message, disable_chat = classify_assistant_error("temporary network issue")

    assert message.startswith("QUILL could not reach the AI provider.")
    assert "Your document was not changed." in message
    assert message.endswith("Details: temporary network issue")
    assert disable_chat is False


def test_a_refused_key_says_where_to_fix_it() -> None:
    message, _ = classify_assistant_error("Error code: 401 - invalid_api_key")
    assert message.startswith("The AI provider did not accept the key")
    assert "Choose Your AI" in message


def test_a_rate_limit_says_wait_then_send_again() -> None:
    message, _ = classify_assistant_error("429 Too Many Requests")
    assert "Wait a minute, then send again." in message


def test_an_unknown_error_is_still_plain_first() -> None:
    message, _ = classify_assistant_error("model produced invalid JSON")
    assert message.startswith("The AI provider returned an error.")
