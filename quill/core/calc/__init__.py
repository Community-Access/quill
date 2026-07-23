"""QUILL Calculator -- a safe scientific expression evaluator plus document-aware
data operations (sum/average/… over selected numbers, CSV, and tables).

wx-free and strict-typed. The evaluator never uses ``eval``: it parses to an AST
and walks an allowlist of operators, functions, and constants, so a document's
text can never execute arbitrary code. See ``evaluator`` and ``data_ops``.
"""

from __future__ import annotations
