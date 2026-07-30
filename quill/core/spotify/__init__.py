"""Spotify integration foundation (pure, wx-free core).

The offline-testable core of QUILL's Spotify support: the OAuth
Authorization-Code-with-PKCE sign-in (:mod:`auth`), the one-shot loopback
redirect receiver (:mod:`auth_callback`), the Web API wrapper
(:mod:`client`), the data model and podcast adapters (:mod:`models`), secret
and consent persistence (:mod:`token_store`, :mod:`consent`), and the
best-effort public-RSS episode matcher (:mod:`rss_match`).

Every network call funnels through exactly one reviewed egress site per
module -- ``auth._token_request`` and ``client._request`` (see
``quill/tools/network_egress_audit.py``). Both accept an injectable opener so
the encoding, refresh, and parsing behaviour is unit-tested without a live
Spotify account. The whole package is ``wx``-free and strict-typed; the
hidden Web Playback engine that actually streams audio lives separately under
``quill/ui/spotify``.

The entire feature is gated behind the ``future.spotify`` flag (locked off),
a one-time network-access consent, Safe-Mode refusal, and -- for playback --
a Spotify Premium account.
"""

from __future__ import annotations
