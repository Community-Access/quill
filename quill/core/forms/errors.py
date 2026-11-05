"""Errors raised by the forms core. Every one carries a GATE-EC code."""

from __future__ import annotations

from quill.core.error_codes import CodedError


class FormError(CodedError):
    """Base for every forms-core failure."""

    code = "QUILL-FORMS-CORE-FAILED"


class FormModelError(FormError):
    """A form model (JSON) that does not fit the model or its schema."""

    code = "QUILL-FORMS-MODEL-INVALID"

    def __init__(self, message: str, problems: list[str] | None = None) -> None:
        super().__init__(message)
        self.problems = list(problems or [])


class FormVersionError(FormModelError):
    """A model newer than this QUILL understands, or with no migration path."""

    code = "QUILL-FORMS-MODEL-VERSION"


class ExpressionError(FormError):
    """An expression (a rule, calculation, score or default) that cannot be read."""

    code = "QUILL-FORMS-EXPR-SYNTAX"

    def __init__(self, message: str, position: int = 0) -> None:
        super().__init__(message)
        #: Where the problem is, in characters of the text.
        self.position = position
        #: The same place in UTF-8 bytes, as BAF reports it (set by ``expr.parse``).
        self.byte_offset = position


class ExpressionEvalError(FormError):
    """An expression that reads but cannot be worked out (divide by zero, a bad date)."""

    code = "QUILL-FORMS-EXPR-EVAL"


class ChoiceLibraryError(FormError):
    """A choice library that does not exist, or whose data file is damaged."""

    code = "QUILL-FORMS-LIBRARY-MISSING"


class FormImportError(FormError):
    """A file from another form tool that cannot be read at all."""

    code = "QUILL-FORMS-IMPORT-UNREADABLE"


class BflError(FormError):
    """BFL with an error in it; ``line`` says where."""

    code = "QUILL-FORMS-BFL-ERROR"

    def __init__(self, message: str, line: int = 0) -> None:
        super().__init__(message)
        self.line = line
