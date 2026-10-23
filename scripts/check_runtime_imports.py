"""Fail a runtime build whose frozen modules cannot actually be imported.

WHY THIS EXISTS
---------------
``check_build_env.py`` guards the floor (everything ``[runtime]`` needs is
importable on the build machine) and ``check_runtime_inventory.py`` guards the
ceiling (nothing undeclared got swept in). Neither can see the failure mode this
gate exists for: a package that *is* in the bundle, *is* found by
``importlib.util.find_spec``, and raises the moment anything imports it.

That is not hypothetical. The 2026-08-17 runtime shipped three broken engines:

- ``vosk`` -- ``OSError: cannot load library 'libvosk.dll'``. The wheel loads its
  26 MB engine DLL through cffi at import time, which PyInstaller's dependency
  analysis does not see, so only vosk's three mingw support DLLs (27.6 MB)
  shipped and the engine itself never did.
- ``faster_whisper`` -- ``ModuleNotFoundError: No module named 'av'``, because
  ``av`` is a deliberate spec exclude.
- ``kokoro_onnx`` -- ``ModuleNotFoundError: No module named 'onnxruntime'``,
  same cause.

Every one of them exited the build at 0. Worse, each shadowed a *working*
on-demand engine pack: PyInstaller's ``FrozenImporter`` sits ahead of
``PathFinder`` on ``sys.meta_path``, so the ``sys.path`` entry
``engine_install.activate_engine_packs`` adds can never win. And because
``is_vosk_available()`` and its siblings ask ``find_spec``, QUILL reported all
three as installed and never offered the engine pack that would have worked.

WHAT IT CHECKS
--------------
Two rules, run *inside the built runtime* (the only place the answer is real):

1. **Engine-pack-owned modules must be ABSENT.** A module the app installs on
   demand must not be frozen in, because frozen wins and cannot be updated.
2. **Everything else declared here must IMPORT, not merely resolve.** A frozen
   module that raises on import is a shipped-broken feature.

Usage::

    python scripts/check_runtime_imports.py <dist-dir>
    python scripts/check_runtime_imports.py <dist-dir> --json <path>

Exits non-zero naming every module that broke a rule.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path

#: Modules installed on demand into ``%APPDATA%\\Quill\\engine-packs`` by
#: ``quill.core.speech.engine_install``. Freezing one shadows the pack for good.
#: Keep in step with ``engine_install._known_pack_dirs`` and the spec excludes.
ENGINE_PACK_OWNED: tuple[str, ...] = (
    "vosk",
    "faster_whisper",
    "ctranslate2",  # faster-whisper's backend; 59 MB with nothing to serve
    "kokoro_onnx",
    "onnxruntime",  # arrives with the kokoro-onnx pack
    "sherpa_onnx",  # nemotron / parakeet / VAD
    # The hub travels WITH the Faster Whisper pack, not with the runtime:
    # engine_install._FASTER_WHISPER_REQUIREMENTS installs
    # ``huggingface_hub>=0.20`` into the pack folder alongside faster-whisper,
    # and no module under quill/ imports it directly (model_mirrors.py moved it
    # off the base dependency deliberately; whisper.cpp fetches its GGML models
    # over plain HTTPS). A frozen copy would therefore serve nobody but the
    # pack -- and shadow the pack's own, pinned copy while doing it, which is
    # the whole failure this list exists to prevent. It was listed under
    # MUST_IMPORT until 2026-08-20, where it demanded a module the 2026-08-19
    # excludes had already made unreachable, so the runtime build could not
    # pass on any machine.
    "huggingface_hub",
)

#: Deliberately bundled and NOT engine-pack-owned, but load native libraries or
#: data at import time -- exactly the shape that fails silently. Each must
#: import cleanly inside the frozen bundle.
MUST_IMPORT: tuple[str, ...] = (
    "wx",
    "numpy",
    "enchant",  # after prune_enchant_payload.py has run
    "yt_dlp",
    "mutagen",
    "soundfile",
    "sounddevice",
    "nacl",
    "cryptography",
    "PIL",
    "quill.core.spellcheck",
    "quill.core.speech.engine_install",
    "quill.ui.audio.mpv_engine",
    # The survivor of the 2026-08-19 undeclared-payload excludes: kept
    # deliberately while a package it can reach for was dropped, so it is one
    # dependency bump away from becoming a shipped-broken feature.
    # keynote_parser and its protobuf/snappy closure are excluded, and this is
    # quill.io.pages Route A. The module must still import and fall through to
    # Route B (LibreOffice / MarkItDown); an ImportError here means .pages files
    # stopped opening at all rather than opening by the other route.
    "quill.io.pages",
    # PDF reading, for File > Open and for Import / Convert Document. The
    # runtime freezes markitdown in (quill[glow] pulls markitdown[all]) but
    # excludes onnxruntime, which markitdown's magika sniffer imports at module
    # top, so markitdown can NEVER import here -- and Import / Convert used to
    # send every PDF to it and fail (2026-10-15). PDFs now go through
    # quill.io.pdf (pdfplumber, then pypdf; pypdfium2 rasterises for OCR), so
    # those are what must import. markitdown is deliberately not listed: it is
    # known-unimportable in this runtime and nothing reaches it for a PDF.
    "pdfplumber",
    "pypdf",
    "pypdfium2",
    "quill.io.pdf",
    "quill.io.docconvert",
    # Quill Social's networks. Social imports them only when an account signs
    # in (quill_social/adapters/registry.py), so a runtime without one would
    # pass every other check and fail at the first Mastodon or Bluesky sign-in
    # (2026-10-23 readiness review).
    "quill_social",
    "mastodon",
    "atproto",
)

#: The Word stack and GLOW's audits; part of MUST_IMPORT, and named on their
#: own so tests/unit/scripts/test_word_support_in_runtime.py can import exactly
#: these with every spec exclude blocked.
WORD_MUST_IMPORT: tuple[str, ...] = (
    # Word documents (2026-10-17). The runtime excluded lxml until then, and
    # python-docx -- pure Python, so it froze in and find_spec found it -- raised
    # the moment it reached for lxml. Every installed QUILL and QUILL Lite opened
    # Word as plain text and could not save a real .docx, and the GLOW audits
    # below failed. The Word round trip (WORD_ROUND_TRIP) proves the rest.
    "lxml.etree",
    "docx",
    "pptx",
    "openpyxl",
    "quill.io.docx_reader",
    "quill.io.docx_writer",
    "quill.core.docx_open",
    "quill.io.word_selfcheck",
    # GLOW's audits, one per format. Every one of them imports
    # acb_large_print.auditor, which imports python-docx at module top -- so a
    # runtime without lxml failed the PDF audit too, not only Word's.
    "quill_glow_core",
    "acb_large_print.auditor",
    "acb_large_print.pdf_auditor",
    "acb_large_print.pptx_auditor",
    "acb_large_print.xlsx_auditor",
)

MUST_IMPORT = MUST_IMPORT + WORD_MUST_IMPORT

#: The functional check run after the imports: write a real .docx, open it the
#: way both editors do, save it back and read the result
#: (quill.io.word_selfcheck). An import can succeed while the job still fails.
WORD_ROUND_TRIP = "quill.io.word_selfcheck"

_PROBE_MODULE = "_quill_import_gate"

_PROBE_SOURCE = '''\
"""Written into the bundle by check_runtime_imports.py; deleted after the run.

Never raises: the runtime is a windowed exe, so an unhandled exception becomes a
modal dialog that blocks the build until somebody clicks it.
"""
import importlib
import importlib.util
import json
import os

ENGINE_PACK_OWNED = {engine_pack!r}
MUST_IMPORT = {must_import!r}

result = {{"absent_violations": [], "import_failures": [], "checked": 0}}

for name in ENGINE_PACK_OWNED:
    try:
        spec = importlib.util.find_spec(name)
    except Exception:
        spec = None
    result["checked"] += 1
    if spec is not None:
        result["absent_violations"].append({{
            "module": name,
            "origin": str(getattr(spec, "origin", "") or ""),
        }})

for name in MUST_IMPORT:
    result["checked"] += 1
    try:
        importlib.import_module(name)
    except Exception as error:
        result["import_failures"].append({{
            "module": name,
            "error": "{{0}}: {{1}}".format(type(error).__name__, error),
        }})

result["checked"] += 1
try:
    problem = importlib.import_module({word_round_trip!r}).word_round_trip_problem()
except Exception as error:
    problem = "{{0}}: {{1}}".format(type(error).__name__, error)
if problem:
    result["import_failures"].append({{
        "module": "Word open and save round trip",
        "error": problem,
    }})

with open(os.environ["QUILL_IMPORT_GATE_OUT"], "w", encoding="utf-8") as handle:
    json.dump(result, handle)
'''


def run_probe(dist: Path, timeout: float = 300.0) -> dict:
    """Run the probe inside *dist*'s frozen runtime and return its report."""
    exe = dist / "QuillVilleRuntime.exe"
    if not exe.is_file():
        raise SystemExit(f"No QuillVilleRuntime.exe in {dist}")
    internal = dist / "_internal"
    if not internal.is_dir():
        raise SystemExit(f"No _internal directory in {dist}")

    # _internal is on the frozen sys.path, so a plain .py dropped there is
    # importable by name -- no rebuild, and nothing ships (it is deleted below).
    probe_path = internal / f"{_PROBE_MODULE}.py"
    with tempfile.TemporaryDirectory() as tmp:
        out_path = Path(tmp) / "import-gate.json"
        probe_path.write_text(
            _PROBE_SOURCE.format(
                engine_pack=list(ENGINE_PACK_OWNED),
                must_import=list(MUST_IMPORT),
                word_round_trip=WORD_ROUND_TRIP,
            ),
            encoding="utf-8",
        )
        try:
            env = dict(os.environ)
            env["QUILL_IMPORT_GATE_OUT"] = str(out_path)
            # QUILL_APP_ROOT is what an installed app sets; without it the
            # bundled-tools search paths are skipped and the probe tests a
            # layout no user ever has.
            env["QUILL_APP_ROOT"] = str(dist)
            subprocess.run(  # noqa: S603 - fixed argv, no shell
                [str(exe), "-m", _PROBE_MODULE],
                env=env,
                timeout=timeout,
                check=False,
                capture_output=True,
            )
            if not out_path.is_file():
                raise SystemExit(
                    "The import gate probe produced no report -- the runtime "
                    "failed to start. Run it by hand:\n"
                    f"  {exe} -m {_PROBE_MODULE}"
                )
            return json.loads(out_path.read_text(encoding="utf-8"))
        finally:
            probe_path.unlink(missing_ok=True)
            for cached in (internal / "__pycache__").glob(f"{_PROBE_MODULE}.*"):
                cached.unlink(missing_ok=True)


def report(result: dict) -> int:
    """Print the outcome; return the process exit code."""
    absent = result.get("absent_violations", [])
    failures = result.get("import_failures", [])

    if absent:
        print("Engine-pack-owned modules were frozen into the runtime:")
        for entry in absent:
            print(f"  {entry['module']}  ({entry['origin'] or 'no origin'})")
        print(
            "\nA frozen copy shadows the on-demand engine pack permanently "
            "(FrozenImporter precedes PathFinder), so the app can never use the "
            "installed one. Add each name to `excludes` in "
            "standalone/runtime/quillville-runtime.spec."
        )
    if failures:
        if absent:
            print()
        print("Frozen modules that are present but cannot be imported:")
        for entry in failures:
            print(f"  {entry['module']}: {entry['error']}")
        print(
            "\nEach of these is a shipped-broken feature. Either restore the "
            "missing dependency or exclude the module so the on-demand path "
            "takes over."
        )
        word_names = {"lxml.etree", "docx", "pptx", "Word open and save round trip"}
        if any(
            entry["module"] in word_names or "docx" in entry["module"] or "acb_" in entry["module"]
            for entry in failures
        ):
            print(
                "\nWord support is broken in this runtime: QUILL and QUILL Lite would "
                "open Word files as plain text, could not save a real .docx, and the "
                "GLOW audits would fail. python-docx needs lxml -- make sure neither "
                "is in `excludes` in standalone/runtime/quillville-runtime.spec and "
                "that both are installed in the build interpreter "
                "(scripts/check_build_env.py --groups runtime,packaging)."
            )
    if absent or failures:
        return 1
    print(f"Runtime import gate: {result.get('checked', 0)} modules checked, all correct.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("dist", type=Path, help="the built QuillVilleRuntime dist dir")
    parser.add_argument("--json", type=Path, default=None, help="also write the raw report here")
    args = parser.parse_args()

    result = run_probe(args.dist.resolve())
    if args.json:
        args.json.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return report(result)


if __name__ == "__main__":
    raise SystemExit(main())
