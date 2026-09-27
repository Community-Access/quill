"""Quill Radio, QUILL Lite and Quill Converter portable bundles carry no GitHub
credential.

All three send all feedback to support@community-access.org by email
(2026-09-26), so none needs feedback-hub or QUILL's bundled GitHub feedback
token. A gitignored ``quill/_feedback_token.py`` left in the checkout by
another app's build used to ride along in the copied ``quill`` source anyway.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest  # type: ignore[import-not-found]

_ROOT = Path(__file__).resolve().parents[3]


def _load_build_portable():
    name = "quill_build_portable_no_token"
    spec = importlib.util.spec_from_file_location(
        name, _ROOT / "standalone" / "studio" / "scripts" / "build_portable.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


bp = _load_build_portable()


@pytest.mark.parametrize("key", ["radio", "quilllite", "converter"])
def test_email_only_apps_carry_no_token_and_no_feedback_hub(key: str) -> None:
    product = bp.PRODUCTS[key]
    assert product.feedback_token is False
    assert "feedback" not in product.dep_groups


def test_other_apps_keep_their_token_until_they_move() -> None:
    assert bp.PRODUCTS["studio"].feedback_token is True


def _checkout(tmp_path: Path) -> Path:
    source = tmp_path / "checkout"
    (source / "quill").mkdir(parents=True)
    (source / "quill" / "__init__.py").write_text("", encoding="utf-8")
    (source / "quill" / "_feedback_token.py").write_text(
        'BUNDLED_TOKEN = "not-a-real-token"\n', encoding="utf-8"
    )
    return source


def test_the_token_file_is_left_out_of_the_bundle(tmp_path: Path) -> None:
    source = _checkout(tmp_path)
    out = tmp_path / "bundle"

    bp._copy_quill_source(out, source, feedback_token=False)

    staged = out / "Lib" / "site-packages" / "quill"
    assert (staged / "__init__.py").is_file()
    assert not (staged / "_feedback_token.py").exists()
    assert (source / "quill" / "_feedback_token.py").is_file()  # the checkout is untouched


def test_a_bundle_that_wants_it_still_requires_it(tmp_path: Path) -> None:
    source = _checkout(tmp_path)
    (source / "quill" / "_feedback_token.py").unlink()

    with pytest.raises(RuntimeError, match="missing"):
        bp._copy_quill_source(tmp_path / "bundle", source, feedback_token=True)
