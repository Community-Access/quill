"""No QuillVille portable bundle carries a GitHub credential or feedback-hub.

Every app sends all feedback to support@community-access.org by email
(owner decision, 2026-09-26), so no bundle needs feedback-hub or QUILL's old
bundled GitHub feedback token. A gitignored ``quill/_feedback_token.py`` left in
the checkout by an older build used to ride along in the copied ``quill``
source; the copy drops it for every product, and the credential gate
(``scripts/check_no_credentials.py``) fails the build if it comes back.
"""

from __future__ import annotations

import dataclasses
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


@pytest.mark.parametrize("key", sorted(bp.PRODUCTS))
def test_no_product_pulls_feedback_hub(key: str) -> None:
    product = bp.PRODUCTS[key]
    assert isinstance(product.dep_groups, tuple)
    assert "feedback" not in product.dep_groups


def test_the_product_model_has_no_token_switch() -> None:
    """A per-product opt-in is how a token could come back for one app."""
    fields = {f.name for f in dataclasses.fields(bp.Product)}
    assert "feedback_token" not in fields


def _checkout(tmp_path: Path) -> Path:
    source = tmp_path / "checkout"
    (source / "quill").mkdir(parents=True)
    (source / "quill" / "__init__.py").write_text("", encoding="utf-8")
    (source / "quill" / "_feedback_token.py").write_text(
        'BUNDLED_TOKEN = "not-a-real-token"\n', encoding="utf-8"
    )
    return source


def test_the_token_file_is_left_out_of_every_bundle(tmp_path: Path) -> None:
    source = _checkout(tmp_path)
    out = tmp_path / "bundle"

    bp._copy_quill_source(out, source)

    staged = out / "Lib" / "site-packages" / "quill"
    assert (staged / "__init__.py").is_file()
    assert not (staged / "_feedback_token.py").exists()
    assert (source / "quill" / "_feedback_token.py").is_file()  # the checkout is untouched


def test_a_checkout_without_the_token_still_builds(tmp_path: Path) -> None:
    source = _checkout(tmp_path)
    (source / "quill" / "_feedback_token.py").unlink()

    bp._copy_quill_source(tmp_path / "bundle", source)  # must not raise

    assert (tmp_path / "bundle" / "Lib" / "site-packages" / "quill" / "__init__.py").is_file()


def test_the_portable_build_runs_the_credential_gate() -> None:
    source = (_ROOT / "standalone" / "studio" / "scripts" / "build_portable.py").read_text(
        encoding="utf-8"
    )
    assert "check_no_credentials.py" in source
