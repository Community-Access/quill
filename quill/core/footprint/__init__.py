"""Footprint measurement helpers (wx-free).

Static size/machine inventory lives in ``scripts/footprint_report.py``; the
live per-engine timing probes (cold-start, first-output, and — via the parent —
peak RSS) live here in :mod:`quill.core.footprint.live_probe`. Both feed the
Phase-0 baseline for the AI footprint & optimization workstream (PRD §5.25f).
"""
