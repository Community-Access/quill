"""Publishing surfaces for finished audiobooks and podcast masters.

Local artifacts (RSS feed generation) plus consent-gated remote destinations
(SFTP upload via QUILL's SSH client, Auphonic post-production). Everything
here is wx-free and strict-typed; every network path is inventoried in
``quill/tools/network_egress_audit.py`` and disabled in Safe Mode by the UI.
"""
