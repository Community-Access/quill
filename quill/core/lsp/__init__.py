"""Layer 4 of IntelliSense: language servers, spoken to over standard input and output.

:mod:`.servers` is the frozen allowlist and how each server is found;
:mod:`.protocol` the wire format; :mod:`.client` one running server;
:mod:`.pool` the running servers, started on first use; :mod:`.convert` what
a server says, in QUILL's own shapes. Pure: no ``wx``. Local only: no server
is allowed the network, and the plan of record is ``docs/design/intellisense.md``.
"""

from __future__ import annotations

from quill.core.lsp.pool import LanguageServerPool, shared_pool
from quill.core.lsp.servers import LANGUAGE_SERVERS, ServerSpec, server_for_path

__all__ = ["LANGUAGE_SERVERS", "LanguageServerPool", "ServerSpec", "server_for_path", "shared_pool"]
