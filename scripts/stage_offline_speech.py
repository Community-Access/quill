"""Stage the offline speech stack into an app payload, from the pinned vault.

WHY THIS EXISTS
---------------
The apps keep their installers small by offering dictation as a consented,
SHA-256-verified download -- which is useless to someone with no internet.
QUILL's Offline Edition answers that by bundling the whisper.cpp engine and a
starter model at the exact paths the resolvers already search:

- ``<root>/tools/speech/whispercpp/``            (whispercpp.engine_search_dirs)
- ``<root>/speech-models-bundled/whispercpp/``   (whispercpp bundled-model path)

This script is that same staging for the *standalone* apps' Offline Editions
(today: Audio Studio). It fetches only from the pinned manifests --
``release_assets.ASSETS`` for the engine, ``model_mirrors`` for the GGML
models -- so an offline bundle is byte-identical to what the online download
path would have fetched, verified the same way. There is one truth about what
a component is, delivered two ways.

Usage::

    python scripts/stage_offline_speech.py --root <dir>              # engine + tiny
    python scripts/stage_offline_speech.py --root <dir> --models tiny,small
    python scripts/stage_offline_speech.py --root <dir> --remove     # unstage

``--remove`` exists because Studio's -Offline build stages into the shared
runtime dist and MUST clean up afterward: a later app build packs that same
dist, and inheriting several hundred megabytes of speech models by accident
is exactly the drift class the runtime gates exist to stop.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT))

#: Matches DEFAULT_BUNDLED_WHISPER_MODEL_ID in build_windows_distribution.py:
#: "tiny" is what guided_setup preselects on first run, so the offline bundle
#: contains the model a fresh install would reach for anyway.
_DEFAULT_MODELS = "tiny"

_ENGINE_SUBDIR = Path("tools") / "speech" / "whispercpp"
_MODELS_SUBDIR = Path("speech-models-bundled") / "whispercpp"


def _stage(root: Path, model_ids: list[str]) -> int:
    from quill.core import release_assets
    from quill.core.speech import model_mirrors

    engine_dir = root / _ENGINE_SUBDIR
    if (engine_dir / "whisper-cli.exe").is_file():
        print(f"engine already staged at {engine_dir}")
    else:
        print("fetching whisper.cpp engine (pinned, verified)...")
        release_assets.fetch_component("whispercpp", engine_dir)
        print(f"  staged {engine_dir}")

    for model_id in model_ids:
        asset = model_mirrors.mirror_for("whispercpp", model_id)
        if asset is None:
            print(f"  no pinned assets-v1 mirror for whispercpp:{model_id} -- refusing")
            return 1
        dest = root / _MODELS_SUBDIR / f"ggml-{model_id}.bin"
        if dest.is_file():
            print(f"  model {model_id} already staged")
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        print(f"fetching ggml-{model_id}.bin (pinned, verified)...")
        model_mirrors.fetch_mirror_file(asset, dest)
        print(f"  staged {dest}  ({dest.stat().st_size / 1024 / 1024:,.0f} MB)")
    return 0


def _remove(root: Path) -> int:
    for subdir in (root / _ENGINE_SUBDIR, root / _MODELS_SUBDIR):
        if subdir.is_dir():
            shutil.rmtree(subdir)
            print(f"removed {subdir}")
    # speech-models-bundled may now be empty; leave no husk behind.
    bundled_root = root / "speech-models-bundled"
    if bundled_root.is_dir() and not any(bundled_root.iterdir()):
        bundled_root.rmdir()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument(
        "--root", type=Path, required=True, help="the app payload root to stage into"
    )
    parser.add_argument(
        "--models",
        default=_DEFAULT_MODELS,
        help=f"comma-separated whisper.cpp model ids (default: {_DEFAULT_MODELS})",
    )
    parser.add_argument("--remove", action="store_true", help="unstage instead of staging")
    args = parser.parse_args()

    root = args.root.resolve()
    if args.remove:
        return _remove(root)
    if not root.is_dir():
        print(f"--root {root} is not a directory")
        return 2
    model_ids = [m.strip() for m in args.models.split(",") if m.strip()]
    return _stage(root, model_ids)


if __name__ == "__main__":
    raise SystemExit(main())
