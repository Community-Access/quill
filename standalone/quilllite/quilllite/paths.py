"""Where QuillLite keeps its state on disk."""

from __future__ import annotations

import os
from pathlib import Path

from quilllite import APP_NAME


def data_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("XDG_DATA_HOME") or str(Path.home())
    path = Path(base) / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def settings_path() -> Path:
    return data_dir() / "settings.json"


def inbox_dir() -> Path:
    path = data_dir() / "inbox"
    path.mkdir(parents=True, exist_ok=True)
    return path


def recovery_dir() -> Path:
    path = data_dir() / "recovery"
    path.mkdir(parents=True, exist_ok=True)
    return path


def pid_file() -> Path:
    return data_dir() / "running.pid"


def comtypes_gen_dir() -> Path:
    path = data_dir() / "comtypes_gen"
    path.mkdir(parents=True, exist_ok=True)
    return path


def lib_dir() -> Path:
    return Path(__file__).resolve().parent / "lib"
