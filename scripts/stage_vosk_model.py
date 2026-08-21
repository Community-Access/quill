"""Stage the bundled Vosk chapter model into a built app folder.

A one-argument wrapper over ``build_windows_distribution._stage_vosk_model`` so
the standalone apps' PowerShell builds can stage the same model, verified the
same way, into their own payload:

    python scripts/stage_vosk_model.py dist/QUILLCast

WHY CAST STAGES A SPEECH MODEL AT ALL
-------------------------------------
Cast works chapters out of a transcript, and for the great majority of podcasts
there is no published transcript to work from -- so the transcript has to be
produced locally or there are no chapters. The engine that does it is 40 MB and
CPU-only, which is the whole reason it was chosen over models thirty-five times
its size: it is small enough to *ship*, so the feature answers the first time
somebody asks instead of opening with a download.

It lands in ``<app>/speech-models-bundled/vosk/<model-id>/``, which is where
``quill.core.speech.providers.vosk._bundled_model_dir`` looks (relative to
``QUILL_APP_ROOT``), so no runtime code has to know a build did this.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.build_windows_distribution import (  # noqa: E402
    _stage_vosk_model,
    _vosk_model_staged,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("app_dir", type=Path, help="The built app folder to stage into.")
    parser.add_argument(
        "--model",
        default="",
        help="Catalog model id; defaults to the recommended small English model.",
    )
    args = parser.parse_args(argv)

    if not args.app_dir.is_dir():
        print(f"error: {args.app_dir} is not a directory", file=sys.stderr)
        return 2
    ok = _stage_vosk_model(args.app_dir, args.model)
    if not ok:
        print("error: the Vosk model did not stage", file=sys.stderr)
        return 1
    print(f"Vosk model staged under {args.app_dir / 'speech-models-bundled' / 'vosk'}")
    return 0


__all__ = ["main", "_vosk_model_staged"]


if __name__ == "__main__":
    raise SystemExit(main())
