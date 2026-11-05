"""Run QAF's form model conformance suite (``tests/conformance/manifest.json``).

The comparison rules are QAF's (``tests/conformance/README.md``): models are
equal when keys and values match, key order aside, numbers compare as numbers
and true is never 1; form-language text is compared byte for byte; errors are
compared by JSON pointer or line, never by wording. The ``builder`` and
``imports`` suites are QAF's own and are skipped here, as the README says.

**Two layouts (wordpress.md 17a.17).** QAF's ``chore/rename-qaf`` keeps the
form-language cases in ``tests/conformance/qaf/``, as ``.qaf`` files, under the
kinds ``qaf-canonical``, ``qaf-legacy`` and ``qaf-errors`` with the case key
``"qaf"``. ``feat/json-form-model``, from before the rename, used ``bfl/``,
``.bfl``, ``bfl-*`` and ``"bfl"``. Both are read: the new layout first.

Each check returns a list of failures (empty when it passed), so a test can
report every failing case at once.
"""

from __future__ import annotations

import atexit
import io
import json
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path
from typing import Any

from quill.core.forms import expr as E
from quill.core.forms import model as M
from quill.core.forms import rules
from quill.core.forms.bfl_read import read
from quill.core.forms.bfl_write import to_bfl
from quill.core.forms.errors import ExpressionError
from quill.core.forms.expr_eval import evaluate
from quill.core.forms.expr_sentence import sentence
from quill.core.forms.schema_check import SCHEMA_PATH

#: The renamed layout first, then the one from before the rename.
QAF_BRANCHES = ("chore/rename-qaf", "feat/json-form-model")
SUITE_KINDS = (
    "schema",
    "expressions",
    "valid-models",
    "invalid-models",
    "behaviour",
    "qaf-canonical",
    "qaf-legacy",
    "qaf-errors",
)
#: A kind's name in the layout from before the rename.
OLD_KINDS = {
    "qaf-canonical": "bfl-canonical",
    "qaf-legacy": "bfl-legacy",
    "qaf-errors": "bfl-errors",
}


def _has_suite(root: Path, *, renamed: bool) -> bool:
    folder = root / "tests" / "conformance"
    return (folder / "manifest.json").is_file() and (folder / "qaf").is_dir() == renamed


def materialize(baf_root: Path) -> Path | None:
    """QAF's suite and schema, read without touching QAF, in a temporary folder.

    In order: the working tree when it has the renamed suite; ``git archive`` of
    each of :data:`QAF_BRANCHES`; then the working tree's older suite. None when
    none of them works.
    """
    if _has_suite(baf_root, renamed=True):
        return baf_root
    for branch in QAF_BRANCHES:
        found = _archive(baf_root, branch)
        if found is not None:
            return found
    return baf_root if _has_suite(baf_root, renamed=False) else None


def _archive(baf_root: Path, branch: str) -> Path | None:
    git = shutil.which("git")
    if git is None:
        return None
    try:
        done = subprocess.run(  # noqa: S603 - read-only: git archive writes to a pipe
            [
                git,
                "-C",
                str(baf_root),
                "archive",
                "--format=tar",
                branch,
                "schema",
                "tests/conformance",
                "docs",
            ],
            capture_output=True,
            check=True,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    target = Path(tempfile.mkdtemp(prefix="quill-qaf-suite-"))
    atexit.register(shutil.rmtree, target, True)
    with tarfile.open(fileobj=io.BytesIO(done.stdout)) as tar:
        tar.extractall(target, filter="data")
    return target


def _source(case: dict[str, Any]) -> str:
    """A case's form-language file or text: ``"qaf"``, or ``"bfl"`` before the rename."""
    return str(case["qaf"] if "qaf" in case else case["bfl"])


class Suite:
    def __init__(self, manifest: Path) -> None:
        self.root = manifest.parent
        self.manifest = json.loads(manifest.read_text(encoding="utf-8"))

    def load(self, rel: str) -> Any:
        return json.loads((self.root / rel).read_text(encoding="utf-8"))

    def text(self, rel: str) -> str:
        return (self.root / rel).read_bytes().decode("utf-8")

    def suites(self, kind: str) -> list[dict[str, Any]]:
        names = {kind, OLD_KINDS.get(kind, kind)}
        return [s for s in self.manifest["suites"] if s["kind"] in names]

    def check(self, kind: str) -> list[str]:
        method = getattr(self, "check_" + kind.replace("-", "_"))
        out: list[str] = []
        for suite in self.suites(kind):
            out.extend(method(suite))
        return out

    def check_schema(self, suite: dict[str, Any]) -> list[str]:
        theirs = (self.root / suite["file"]).resolve()
        if not theirs.is_file() or theirs == SCHEMA_PATH.resolve():
            return []
        if theirs.read_bytes() != SCHEMA_PATH.read_bytes():
            return ["QUILL's schema file differs from QAF's"]
        return []

    def check_expressions(self, suite: dict[str, Any]) -> list[str]:
        d = self.load(suite["file"])
        out = []
        for c in d["parse"]:
            try:
                node = E.parse(c["text"])
            except ExpressionError as exc:
                out.append(f"parse {c['text']!r}: {exc}")
                continue
            if E.to_text(node) != c["canonical"]:
                out.append(f"canonical {c['text']!r}: {E.to_text(node)!r}")
            if "ast" in c and not M.same(node, c["ast"]):
                out.append(f"ast {c['text']!r}")
            if "sentence" in c and sentence(node, d["labels"], d["choices"]) != c["sentence"]:
                out.append(f"sentence {c['text']!r}: {sentence(node, d['labels'], d['choices'])!r}")
        for c in d["errors"]:
            try:
                E.parse(c["text"])
            except ExpressionError as exc:
                if "offset" in c and exc.byte_offset != c["offset"]:
                    out.append(f"error {c['text']!r} at byte {exc.byte_offset}, not {c['offset']}")
            else:
                out.append(f"accepted the error case {c['text']!r}")
        for c in d["evaluate"]:
            got = evaluate(c["text"], d["context"])
            if not M.same(got, c["result"]):
                out.append(f"evaluate {c['text']!r}: {got!r}, not {c['result']!r}")
        return out

    def check_valid_models(self, suite: dict[str, Any]) -> list[str]:
        return [
            f"{f}: {M.validate(self.load(f))[:2]}"
            for f in suite["files"]
            if M.validate(self.load(f))
        ]

    def check_invalid_models(self, suite: dict[str, Any]) -> list[str]:
        out = []
        for c in self.load(suite["file"])["cases"]:
            found = M.validate(c["model"])
            if not any(e["path"] == c["path"] for e in found):
                out.append(f"{c['name']}: no error at {c['path']} ({found[:2]})")
        return out

    def check_behaviour(self, suite: dict[str, Any]) -> list[str]:
        d = self.load(suite["file"])
        base = Path(suite["file"]).parent
        out = []
        for c in d["cases"]:
            model = self.load(str(base / c["model"]))
            extra = {"today": d.get("today")}
            if "scores" in c:
                got = rules.score(model, c["answers"])
                if not M.same(got["fields"], c["scores"]) or not M.same(got["total"], c["total"]):
                    out.append(f"{c['name']}: scores {got}")
            if "outcome" in c:
                found = rules.outcome(model, c["answers"], extra)
                if (found or {}).get("id") != c["outcome"]:
                    out.append(f"{c['name']}: outcome {found}")
            for i in c.get("shown", []):
                if not rules.is_shown(model, i, c["answers"], extra):
                    out.append(f"{c['name']}: {i} hidden")
            for i in c.get("hidden", []):
                if rules.is_shown(model, i, c["answers"], extra):
                    out.append(f"{c['name']}: {i} shown")
        return out

    def check_qaf_canonical(self, suite: dict[str, Any]) -> list[str]:
        out = []
        for c in suite["cases"]:
            name = _source(c)
            model, bfl = self.load(c["model"]), self.text(name)
            if to_bfl(model) != bfl:
                out.append(f"{name}: the model does not write as the file")
            result = read(bfl)
            if result.errors or result.warnings or not M.same(result.model, model):
                out.append(
                    f"{name}: does not read back to the model ({result.errors[:1]}{result.warnings[:1]})"  # noqa: E501
                )
            if M.validate(model):
                out.append(f"{c['model']}: not valid")
        return out

    def check_qaf_legacy(self, suite: dict[str, Any]) -> list[str]:
        out = []
        for c in suite["cases"]:
            name = _source(c)
            result = read(self.text(name))
            model = self.load(c["model"])
            if result.errors or not M.same(result.model, model):
                out.append(f"{name}: does not read to the model ({result.errors[:1]})")
            if to_bfl(model) != self.text(c["canonical"]):
                out.append(f"{c['canonical']}: the model does not write as the file")
            for crlf in (self.text(name).replace("\n", "\r\n"), "﻿" + self.text(name)):
                if not M.same(read(crlf).model, model):
                    out.append(f"{name}: CRLF or a byte order mark changes what it reads to")
        return out

    def check_qaf_errors(self, suite: dict[str, Any]) -> list[str]:
        out = []
        for c in self.load(suite["file"])["cases"]:
            lines = [e["line"] for e in read(_source(c)).errors]
            if c["line"] not in lines:
                out.append(f"{c['name']}: errors on lines {lines}, not {c['line']}")
        return out

    def case_count(self) -> int:
        n = 0
        for s in self.manifest["suites"]:
            if s.get("baf_only"):
                continue
            n += len(s.get("cases", s.get("files", [None])))
        return n
