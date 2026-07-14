"""Quill Eraser engine: orchestrates rules against scoped document text."""

from __future__ import annotations

from quill.core.hygiene.findings import HygieneContext, HygieneFinding, HygieneSettings
from quill.core.hygiene.ignored_ranges import compute_ignored_ranges
from quill.core.hygiene.rules import BUILTIN_RULES, HygieneRule

# File extensions treated as code/structured text — prose rules are suppressed.
_CODE_EXTENSIONS: frozenset[str] = frozenset({
    "py",
    "js",
    "ts",
    "jsx",
    "tsx",
    "java",
    "c",
    "cpp",
    "cs",
    "go",
    "rs",
    "rb",
    "php",
    "html",
    "htm",
    "css",
    "scss",
    "sass",
    "json",
    "yaml",
    "yml",
    "toml",
    "ini",
    "cfg",
    "sh",
    "bash",
    "zsh",
    "h",
    "hpp",
    "swift",
    "kt",
    "scala",
    "r",
    "lua",
    "sql",
    "xml",
})

# Extensions where indentation carries semantic meaning.
_INDENT_SENSITIVE: frozenset[str] = frozenset({"py", "yaml", "yml"})

_SAFE_ONLY_RULES: frozenset[str] = frozenset({"prose.trailing_spaces"})


class HygieneEngine:
    """Run hygiene rules against document text and return findings."""

    def __init__(self, extra_rules: list[HygieneRule] | None = None) -> None:
        self._rules: list[HygieneRule] = list(BUILTIN_RULES) + (extra_rules or [])

    @staticmethod
    def is_code_file(file_ext: str) -> bool:
        return file_ext.lower() in _CODE_EXTENSIONS

    @staticmethod
    def is_indent_sensitive(file_ext: str) -> bool:
        return file_ext.lower() in _INDENT_SENSITIVE

    def check(
        self,
        text: str,
        *,
        file_ext: str = "",
        scope_start: int = 0,
        scope_end: int | None = None,
        settings: HygieneSettings | None = None,
        safe_only: bool = False,
    ) -> list[HygieneFinding]:
        """
        Scan *text* (or the slice ``text[scope_start:scope_end]``) and return findings.

        Parameters
        ----------
        text:
            Full document text.
        file_ext:
            Lowercase file extension without dot (e.g. ``"py"``).
        scope_start / scope_end:
            Byte offsets into *text* to limit scanning; findings outside the
            scope are excluded.  Default: full document.
        settings:
            Rule configuration; defaults are used when ``None``.
        safe_only:
            When ``True``, suppress all rules except those in ``_SAFE_ONLY_RULES``.
            Used when the user chooses "safe checks only" on a code file.
        """
        if settings is None:
            settings = HygieneSettings()
        if scope_end is None:
            scope_end = len(text)

        scoped = text[scope_start:scope_end]
        is_markdown = file_ext.lower() == "md"

        ignored = compute_ignored_ranges(scoped, is_markdown=is_markdown)
        context = HygieneContext(
            text=scoped,
            file_ext=file_ext.lower(),
            scope_start=0,
            scope_end=len(scoped),
            ignored_ranges=ignored,
            settings=settings,
        )

        is_code = self.is_code_file(file_ext)
        findings: list[HygieneFinding] = []

        for rule in self._rules:
            if not settings.is_rule_enabled(rule.id):
                continue
            if is_code and not safe_only and rule.id not in _SAFE_ONLY_RULES:
                continue
            if safe_only and rule.id not in _SAFE_ONLY_RULES:
                continue
            if not settings.confidence_passes("high") and rule.id in {
                "prose.multiple_spaces",
                "prose.trailing_spaces",
                "prose.space_before_punctuation",
                "prose.excessive_blank_lines",
            }:
                pass
            for f in rule.check(scoped, context):
                if not settings.confidence_passes(f.confidence):
                    continue
                # Re-base offsets relative to scope_start for caller convenience
                findings.append(
                    HygieneFinding(
                        rule_id=f.rule_id,
                        title=f.title,
                        description=f.description,
                        confidence=f.confidence,
                        start_offset=f.start_offset + scope_start,
                        end_offset=f.end_offset + scope_start,
                        line=f.line,
                        column=f.column,
                        original_text=f.original_text,
                        suggested_text=f.suggested_text,
                        can_auto_fix=f.can_auto_fix,
                    )
                )

        # Deduplicate overlapping findings (keep earliest start, then highest confidence).
        _conf = {"high": 0, "medium": 1, "low": 2}
        findings.sort(key=lambda f: (f.start_offset, _conf[f.confidence]))
        seen: list[HygieneFinding] = []
        for f in findings:
            if seen and f.start_offset < seen[-1].end_offset:
                continue
            seen.append(f)

        return seen

    @staticmethod
    def apply_fix(text: str, finding: HygieneFinding) -> str | None:
        """Apply *finding*'s suggested fix to *text* and return the result.

        Returns ``None`` if the original text at the expected location has
        changed (document was edited between scan and apply).
        """
        if finding.suggested_text is None:
            return None
        actual = text[finding.start_offset : finding.end_offset]
        if actual != finding.original_text:
            return None
        return text[: finding.start_offset] + finding.suggested_text + text[finding.end_offset :]
