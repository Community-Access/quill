"""The Practice Site's npm lock is the one the build installs from.

``scripts/fetch_language_servers.fetch_wp_playground`` runs ``npm ci`` against
``scripts/wp_playground/package-lock.json`` only when the lock resolves every
direct pin; otherwise it falls back to ``npm install`` and the build is no
longer reproducible. These tests keep the lock, ``package.json`` and the pin
in the code agreeing, and every package coming from the public registry with
an integrity hash.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

from quill.core.wordpress.workbench_practice import PLAYGROUND_CLI_VERSION

_ROOT = Path(__file__).resolve().parents[3]
_DIR = _ROOT / "scripts" / "wp_playground"


def _fetcher():
    path = _ROOT / "scripts" / "fetch_language_servers.py"
    spec = importlib.util.spec_from_file_location("fetch_language_servers_lock", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _json(name: str) -> dict:
    return json.loads((_DIR / name).read_text(encoding="utf-8"))


def test_package_json_pins_the_cli_the_code_expects() -> None:
    assert _json("package.json")["dependencies"] == {"@wp-playground/cli": PLAYGROUND_CLI_VERSION}


def test_the_lock_matches_package_json() -> None:
    package = _json("package.json")
    lock = _json("package-lock.json")
    assert lock["name"] == package["name"]
    assert lock["lockfileVersion"] >= 2
    assert lock["packages"][""]["dependencies"] == package["dependencies"]
    cli = lock["packages"]["node_modules/@wp-playground/cli"]
    assert cli["version"] == PLAYGROUND_CLI_VERSION


def test_the_build_installs_with_npm_ci_from_this_lock() -> None:
    fetcher = _fetcher()
    assert fetcher.PLAYGROUND_DIR == _DIR
    assert fetcher._lock_matches_packages(_DIR / "package-lock.json", fetcher.PLAYGROUND_PACKAGES)


def test_every_locked_package_comes_from_the_registry_with_a_hash() -> None:
    packages = _json("package-lock.json")["packages"]
    for name, entry in packages.items():
        if not name:
            continue
        assert entry.get("resolved", "").startswith("https://registry.npmjs.org/"), name
        assert entry.get("integrity", "").startswith("sha512-"), name


def test_the_lock_is_lf_only() -> None:
    assert b"\r\n" not in (_DIR / "package-lock.json").read_bytes()
