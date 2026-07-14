"""Unit tests for quill.core.token_nav (issue #181)."""

from __future__ import annotations

from quill.core.token_nav import classify_token, next_token_position, prev_token_position

_PY_KEYWORDS = ("def", "class", "return", "if", "else", "for", "while", "import")


class TestNextTokenPosition:
    def test_finds_identifier(self) -> None:
        pos, tok = next_token_position("  hello world", 0)
        assert tok == "hello"
        assert pos == 2

    def test_advances_past_cursor(self) -> None:
        text = "foo bar baz"
        pos, tok = next_token_position(text, 4)
        assert tok == "bar"

    def test_end_of_text_returns_empty(self) -> None:
        pos, tok = next_token_position("hello", 10)
        assert tok == ""

    def test_finds_number(self) -> None:
        _, tok = next_token_position("x = 42", 2)
        assert tok in ("=", "42")

    def test_finds_operator(self) -> None:
        pos, tok = next_token_position("x += 1", 1)
        assert tok == "+="

    def test_finds_string(self) -> None:
        _, tok = next_token_position('print("hello")', 5)
        assert '"hello"' in tok or tok == "("

    def test_cursor_at_start(self) -> None:
        pos, tok = next_token_position("abc def", 0)
        assert tok == "abc"
        assert pos == 0


class TestPrevTokenPosition:
    def test_finds_previous_word(self) -> None:
        text = "foo bar baz"
        pos, tok = prev_token_position(text, 8)
        assert tok == "bar"
        assert pos == 4

    def test_at_start_returns_empty(self) -> None:
        pos, tok = prev_token_position("hello world", 0)
        assert tok == ""

    def test_finds_last_before_cursor(self) -> None:
        text = "x = 42"
        pos, tok = prev_token_position(text, 6)
        assert tok == "42"

    def test_multiple_tokens(self) -> None:
        text = "a b c d"
        pos, tok = prev_token_position(text, 6)
        assert tok == "c"

    def test_operator_before_cursor(self) -> None:
        text = "x += 1"
        pos, tok = prev_token_position(text, 4)
        assert tok == "+="


class TestClassifyToken:
    def test_keyword(self) -> None:
        assert classify_token("def", _PY_KEYWORDS) == "keyword: def"

    def test_identifier(self) -> None:
        assert classify_token("my_function", _PY_KEYWORDS) == "identifier: my_function"

    def test_integer(self) -> None:
        assert classify_token("42", ()) == "number: 42"

    def test_float(self) -> None:
        assert classify_token("3.14", ()) == "number: 3.14"

    def test_hex(self) -> None:
        assert classify_token("0xFF", ()) == "number: 0xFF"

    def test_open_paren(self) -> None:
        assert classify_token("(", ()) == "open paren"

    def test_close_paren(self) -> None:
        assert classify_token(")", ()) == "close paren"

    def test_open_brace(self) -> None:
        assert classify_token("{", ()) == "open brace"

    def test_close_brace(self) -> None:
        assert classify_token("}", ()) == "close brace"

    def test_open_bracket(self) -> None:
        assert classify_token("[", ()) == "open bracket"

    def test_close_bracket(self) -> None:
        assert classify_token("]", ()) == "close bracket"

    def test_operator(self) -> None:
        result = classify_token("+=", ())
        assert result.startswith("operator:")

    def test_string_token(self) -> None:
        result = classify_token('"hello"', ())
        assert result.startswith("string:")

    def test_empty_token(self) -> None:
        assert classify_token("", ()) == ""

    def test_non_keyword_word(self) -> None:
        result = classify_token("my_var", _PY_KEYWORDS)
        assert result == "identifier: my_var"
