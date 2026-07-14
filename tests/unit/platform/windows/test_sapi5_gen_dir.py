"""comtypes' codegen cache is redirected to a writable location so SAPI 5 can
initialise even under a read-only (Program Files) install."""

from __future__ import annotations

import pytest

from quill.platform.windows import sapi5


def test_gen_dir_is_writable_or_in_memory() -> None:
    if sapi5._cc is None:
        pytest.skip("comtypes is not available on this platform")
    gen_dir = sapi5._cc.gen_dir
    # Either our per-user cache folder, or in-memory codegen (None) as a fallback.
    assert gen_dir is None or str(gen_dir).endswith("comtypes_gen")


def test_redirect_is_idempotent_and_safe() -> None:
    # Calling it again must not raise, regardless of comtypes availability.
    sapi5._redirect_comtypes_gen_dir()
    if sapi5._cc is not None:
        gen_dir = sapi5._cc.gen_dir
        assert gen_dir is None or str(gen_dir).endswith("comtypes_gen")
