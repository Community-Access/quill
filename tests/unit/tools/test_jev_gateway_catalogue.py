"""The gateway's copy of the Command Key catalogue matches QUILL's (command-key.md 7.4, 7.6).

``/v1/decide`` builds the Jev request from ``quill-ai-gateway/app/jev_catalogue``
and its own copy of the question builder. If either drifted from QUILL's, the
gateway route and the own-key route would ask Jev different questions about the
same sentence, and nobody would hear the difference until the answers got worse.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from quill.core.command_catalogue import rows_for_app
from quill.core.command_catalogue.jev_request import (
    CATALOGUE_VERSION,
    JEV_MODEL,
    MAX_CANDIDATES,
    MAX_REQUEST_CHARS,
    NONE_OF_THESE,
    _questions,
)
from quill.core.command_catalogue.resolver import Candidate
from quill.tools import build_jev_gateway_catalogue as tool

_GATEWAY_JEV = Path(__file__).resolve().parents[3] / "quill-ai-gateway" / "app" / "jev.py"


def _gateway():
    spec = importlib.util.spec_from_file_location("quill_ai_gateway_jev", _GATEWAY_JEV)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # A dataclass looks its module up in sys.modules while it is being built.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_the_snapshot_for_this_catalogue_version_is_current() -> None:
    assert tool.main(["--check"]) == 0, (
        "run: python -m quill.tools.build_jev_gateway_catalogue --write"
    )


def test_the_gateway_pins_what_the_client_pins() -> None:
    gateway = _gateway()
    assert gateway.JEV_MODEL == JEV_MODEL
    assert gateway.MAX_CANDIDATES == MAX_CANDIDATES
    assert gateway.MAX_REQUEST_CHARS == MAX_REQUEST_CHARS
    assert gateway.NONE_OF_THESE == NONE_OF_THESE


def test_the_gateway_asks_the_same_questions() -> None:
    gateway = _gateway()
    rows = gateway.catalogue(CATALOGUE_VERSION)
    for app in tool.APPS:
        offered = [spec for spec in rows_for_app(app) if spec.offered]
        for start in range(0, len(offered), 7):
            chosen = offered[start : start + 7]
            ids = [spec.id for spec in chosen]
            for with_correction in (False, True):
                client = _questions([Candidate(spec) for spec in chosen], with_correction)
                server = gateway.build_questions(rows[app], ids, with_correction)
                assert server == client, (app, ids, with_correction)
