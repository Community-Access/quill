"""The ``QUILL-AUTH-*`` error family carries stable, unique, well-formed codes."""

from __future__ import annotations

import re

import pytest

from quill.core.auth import (
    AuthError,
    FlowStateMismatchError,
    FlowTimeoutError,
    ProviderConfigError,
    ProviderUnknownError,
    RefreshInvalidGrantError,
    TokenUnavailableError,
)
from quill.core.error_codes import CodedError

_CODE_RE = re.compile(r"^QUILL-AUTH-[A-Z0-9]+(-[A-Z0-9]+){0,3}$")

_ALL = [
    AuthError,
    ProviderUnknownError,
    ProviderConfigError,
    FlowStateMismatchError,
    FlowTimeoutError,
    RefreshInvalidGrantError,
    TokenUnavailableError,
]


@pytest.mark.parametrize("cls", _ALL)
def test_is_coded_error(cls: type[AuthError]) -> None:
    assert issubclass(cls, AuthError)
    assert issubclass(cls, CodedError)


@pytest.mark.parametrize("cls", _ALL)
def test_code_shape(cls: type[AuthError]) -> None:
    assert _CODE_RE.match(cls.code), cls.code


@pytest.mark.smoke
def test_codes_are_unique() -> None:
    codes = [cls.code for cls in _ALL]
    assert len(codes) == len(set(codes))


def test_code_prefixes_message() -> None:
    err = ProviderUnknownError("no provider registered as 'bard'")
    assert str(err) == "[QUILL-AUTH-PROVIDER-UNKNOWN] no provider registered as 'bard'"
