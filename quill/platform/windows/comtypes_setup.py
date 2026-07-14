"""Shared comtypes generated-wrapper cache redirect (Windows-only).

comtypes writes generated Python wrappers for any COM type library it
touches (SAPI's ``SpVoice``, Rich Edit's TOM, oleacc for Narrator's UIA
bridge, ...) to disk on first use. Its default location is inside the
comtypes package itself, which is read-only under a per-machine install
(e.g. Program Files without administrator elevation) -- the write fails
there and the COM call degrades or raises for no good reason.

Every comtypes call site in QUILL calls :func:`ensure_comtypes_gen_dir_redirected`
before touching comtypes, rather than relying on some other module (e.g.
``sapi5``) having already imported and set the process-wide
``comtypes.client.gen_dir`` as a side effect -- import order between SAPI,
Narrator's UIA bridge, and the Rich Edit TOM surface is not something QUILL
controls or should have to reason about (BITS mailing list report, 2026-07-11:
a per-machine install without elevation).
"""

from __future__ import annotations

try:  # comtypes is Windows-only and is a direct dependency on Windows.
    import comtypes.client as _cc  # type: ignore[import-untyped]
except Exception:  # noqa: BLE001 - any import failure just means no comtypes
    _cc = None

_redirected = False


def ensure_comtypes_gen_dir_redirected() -> None:
    """Point comtypes' generated-wrapper cache at a writable per-user folder.

    Idempotent and cheap to call from every comtypes call site -- the real
    filesystem work only happens once per process. Falls back to in-memory
    codegen (``gen_dir = None``) if even the per-user data dir is
    unavailable, so comtypes still works without any disk write.
    """
    global _redirected
    if _redirected or _cc is None:
        return
    _redirected = True
    try:
        from quill.core.paths import app_data_dir

        gen_dir = app_data_dir() / "comtypes_gen"
        gen_dir.mkdir(parents=True, exist_ok=True)
        _cc.gen_dir = str(gen_dir)
    except Exception:  # noqa: BLE001 - never let cache setup break a caller
        try:
            _cc.gen_dir = None  # in-memory codegen; no disk write required
        except Exception:  # noqa: BLE001
            pass


__all__ = ["ensure_comtypes_gen_dir_redirected"]
