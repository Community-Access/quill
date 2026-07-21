"""Network adapters (PRD 6.3, 22, 23).

Each adapter isolates one network behind a common contract so the domain and UI
never branch on network name -- they ask the adapter and the capability
registry. The mock adapter drives the entire P0 experience with no credentials;
the Mastodon and Bluesky adapters declare their capabilities and mark the exact
boundary where a live client library is required.
"""

from quill_social.adapters.base import (
    AdapterError,
    NetworkAdapter,
    PublishRequest,
    PublishResult,
)

__all__ = [
    "AdapterError",
    "NetworkAdapter",
    "PublishRequest",
    "PublishResult",
]
