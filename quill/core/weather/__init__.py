"""QUILL Weather -- accessible, text-first weather from official free sources.

The 2.1.0 slice of the QUILL Weather PRD (docs/QUILL-Weather-PRD.md in the Quill
Radio repo): a top-level Weather menu that resolves a location, then shows
current conditions, the period forecast, and -- most importantly -- any active
watches, warnings, and advisories, entirely as reviewable text. Speech,
Weather Guardian background monitoring, Voice Studio, the alert relay, and the
NOAA Weather Radio explorer are later PRD phases; nothing here presumes them.

Everything in this package is wx-free, strict-typed, HTTPS-only, egress-audited
(see ``quill/tools/network_egress_audit.py``), and disabled in Safe Mode. Two
free, no-account providers back it: Zippopotam.us resolves a US ZIP or
city/state to coordinates, and the National Weather Service API
(``api.weather.gov``) supplies the point metadata, forecast, latest
observation, and active alerts. Neither needs a key; NWS only asks for an
identifying User-Agent and no more than one alert poll every 30 seconds.
"""

from __future__ import annotations
