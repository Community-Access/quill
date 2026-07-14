"""Node.js runtime bridge for Quillins with ``"runtime": "node"``.

Issue #158: this module is the thin Python-side wrapper that drives a Node.js
Quillin handler.  It delegates all subprocess management to
:mod:`quill.core.ai.external_engine` so the Node executable is checked against
the same allowlist and the same master consent switch used by AI engines.

Protocol (Quillin stdio / JSONL)
---------------------------------
Request (QUILL -> Node, one JSON line):

.. code-block:: json

    {"method": "<handler_name>", "params": {"capabilities": [...], "context": {...}}}

Response (Node -> QUILL, one JSON line):

.. code-block:: json

    {"result": null, "actions": [{"type": "announce", "args": ["Hello"]}]}

or on error:

.. code-block:: json

    {"error": "Something went wrong"}

The ``context`` object carries editor state the handler may read (``selection``,
``text``, ``cursor_offset``, etc.).  The handler returns *actions* it wants the
host to perform; the host dispatches them through the capability-gated
:class:`~quill.core.quillins.host.HostServices` in declaration order.

This is the "context in, actions out" model rather than the full bidirectional
protocol used by Python Quillins.  It is simpler and works well for stateless
text-processing handlers; interactive handlers that need mid-execution prompts
should use the Python runtime.
"""

from __future__ import annotations

import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

from quill.core.ai.external_engine import (
    EngineConfig,
    EngineResult,
    JsonlRequest,
    Runner,
    run_request,
)
from quill.core.quillins.host import HostServices
from quill.core.quillins.model import ExtensionManifest, QuillinError

# Action types the Node worker may return.  Any other type is silently skipped
# so future action types are backwards-compatible.
_DISPATCH_ACTIONS: frozenset[str] = frozenset({
    "replace_selection",
    "insert_text",
    "set_text",
    "open_buffer",
    "announce",
    "set_status",
})


def run_node_command(
    manifest: ExtensionManifest,
    directory: Path,
    command_id: str,
    context: dict[str, Any],
    services: HostServices,
    *,
    master_enabled: bool | None = None,
    node_executable: str | None = None,
    timeout: float = 30.0,
    runner: Runner | None = None,
    which: Callable[[str], str | None] | None = None,
) -> EngineResult:
    """Invoke a Node Quillin handler and apply the returned actions.

    Looks up the handler function name for ``command_id`` in the manifest,
    sends a single JSONL request to the Node process (started with
    ``node <main.js>``), then dispatches any ``actions`` in the response
    through ``services``.

    ``context`` is supplied by the caller (typically the UI layer) and should
    include whatever editor state the handler needs.  Common keys::

        {
            "selection": "selected text",
            "text": "full document text",
            "cursor_offset": 42,
        }

    Returns the raw :class:`~quill.core.ai.external_engine.EngineResult`; the
    caller may inspect ``.ok`` and ``.error`` for diagnostics.  Actions are
    dispatched before returning, so side-effects (announce, replace_selection,
    etc.) are already applied on success.

    Raises :class:`~quill.core.quillins.model.QuillinError` for manifest-level
    problems (no ``main``, unknown ``command_id``).
    """

    if manifest.main is None:
        raise QuillinError("node Quillin manifest has no 'main' module")

    if node_executable is None:
        try:
            from quill.core.node_install import node_executable_path

            managed = node_executable_path()
            node_executable = str(managed) if managed is not None else "node"
        except Exception:  # noqa: BLE001 - degrade gracefully; probe_engine will surface the error
            node_executable = "node"

    handler_name = _handler_for(manifest, command_id)
    config = EngineConfig(
        engine_id=f"quillin.node.{manifest.id}",
        command=(node_executable, str(directory / manifest.main)),
        enabled=True,
    )
    request = JsonlRequest(
        method=handler_name,
        params={
            "capabilities": list(manifest.capabilities),
            "context": context,
        },
    )

    run_kwargs: dict[str, Any] = {"master_enabled": master_enabled, "timeout": timeout}
    if runner is not None:
        run_kwargs["runner"] = runner
    run_kwargs["which"] = which if which is not None else shutil.which
    result = run_request(config, request, **run_kwargs)
    if not result.ok:
        return result

    response = result.response or {}
    for action in response.get("actions", []):
        if isinstance(action, dict):
            _dispatch_action(action, services)

    return result


def _handler_for(manifest: ExtensionManifest, command_id: str) -> str:
    for command in manifest.contributes.commands:
        if command.id == command_id:
            if command.handler is None:
                raise QuillinError(f"command '{command_id}' is a snippet, not a handler")
            return command.handler
    raise QuillinError(f"unknown command: {command_id}")


def _dispatch_action(action: dict[str, Any], services: HostServices) -> None:
    action_type = str(action.get("type", ""))
    if action_type not in _DISPATCH_ACTIONS:
        return
    args: list[Any] = action.get("args", [])
    if not isinstance(args, list):
        args = []

    def _arg(index: int, default: str = "") -> str:
        return str(args[index]) if index < len(args) else default

    if action_type == "replace_selection":
        services.replace_selection(_arg(0))
    elif action_type == "insert_text":
        services.insert_text(_arg(0))
    elif action_type == "set_text":
        services.set_text(_arg(0))
    elif action_type == "open_buffer":
        services.open_buffer(_arg(0), _arg(1))
    elif action_type == "announce":
        if not services.is_verbosity_speech_enabled():
            return
        services.announce(_arg(0))
    elif action_type == "set_status":
        services.set_status(_arg(0))
