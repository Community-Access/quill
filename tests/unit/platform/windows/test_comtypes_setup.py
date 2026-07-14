"""The shared comtypes generated-wrapper cache redirect (BITS mailing list
report, 2026-07-11): every comtypes call site redirects the cache itself
rather than relying on some other module having already done it as an
import-order side effect."""

from __future__ import annotations

import pytest

from quill.platform.windows import comtypes_setup


def test_gen_dir_is_writable_or_in_memory() -> None:
    if comtypes_setup._cc is None:
        pytest.skip("comtypes is not available on this platform")
    comtypes_setup.ensure_comtypes_gen_dir_redirected()
    gen_dir = comtypes_setup._cc.gen_dir
    # Either our per-user cache folder, or in-memory codegen (None) as a fallback.
    assert gen_dir is None or str(gen_dir).endswith("comtypes_gen")


def test_redirect_is_idempotent_and_safe() -> None:
    # Calling it repeatedly must not raise, regardless of comtypes availability.
    comtypes_setup.ensure_comtypes_gen_dir_redirected()
    comtypes_setup.ensure_comtypes_gen_dir_redirected()
    if comtypes_setup._cc is not None:
        gen_dir = comtypes_setup._cc.gen_dir
        assert gen_dir is None or str(gen_dir).endswith("comtypes_gen")


def test_second_call_skips_the_filesystem_work(monkeypatch: pytest.MonkeyPatch) -> None:
    """The module-level ``_redirected`` flag makes repeat calls a no-op --
    every comtypes call site (SAPI, Narrator's oleacc bridge, the Rich Edit
    TOM surface) can call this unconditionally without repeated mkdir/attribute
    churn on every COM interaction."""
    if comtypes_setup._cc is None:
        pytest.skip("comtypes is not available on this platform")
    comtypes_setup.ensure_comtypes_gen_dir_redirected()
    assert comtypes_setup._redirected is True

    def _boom() -> None:
        raise AssertionError("app_data_dir must not be reached once already redirected")

    monkeypatch.setattr("quill.core.paths.app_data_dir", _boom)
    comtypes_setup.ensure_comtypes_gen_dir_redirected()  # must not raise
