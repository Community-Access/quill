"""Where Next Block and Previous Block stop, language by language.

A block in prose is a paragraph. In code it is the unit a reader of the
language thinks in: a Python ``def``, a C# class, an INI section, a batch
label, a LaTeX ``\\section``, an HTML heading or landmark. Each pattern here is
a regular expression matched per line (``re.MULTILINE``) whose matches begin
those units; :mod:`quill.core.language_profile` hangs one on each profile.

Heuristics, deliberately. A stop on a line that only looks like a declaration
costs one extra key press; a parser per language would cost a dependency per
language and a failure mode per parser. Markdown and plain text have no pattern
and keep paragraph blocks.

Pure data, no ``wx``.
"""

from __future__ import annotations

_C_FAMILY_MODIFIERS = (
    r"(?:public|private|protected|internal|static|abstract|sealed|partial|final|"
    r"readonly|async|virtual|override|extern|unsafe|new|synchronized|native|"
    r"default|strictfp)"
)

#: C#, Java and Kotlin-shaped declarations: types with or without modifiers
#: (and C# attributes in front), and methods with at least one modifier, a name
#: and an open parenthesis on a line that does not end in a semicolon.
C_FAMILY = (
    r"^[ \t]*(?:\[[^\]\n]*\][ \t]*)*(?:" + _C_FAMILY_MODIFIERS + r"[ \t]+)*"
    r"(?:class|interface|struct|enum|record|namespace)[ \t]+\w"
    r"|^[ \t]*(?:" + _C_FAMILY_MODIFIERS + r"[ \t]+)+[\w<>\[\],.?]+(?:[ \t]+\w+)?"
    r"[ \t]*\((?![^\n]*;[ \t]*$)"
)

_JS_METHOD = (
    r"|^[ \t]+(?:(?:static|async|get|set|public|private|protected|readonly|override)[ \t]+)*"
    r"(?!(?:if|for|while|switch|catch|with|return|function|else|do)\b)"
    r"[A-Za-z_$#][\w$]*[ \t]*\([^;\n]*\)[ \t]*(?::[^{;\n]+)?\{"
)

#: Functions, classes, functions assigned to a name, and methods in a class.
JAVASCRIPT = (
    r"^[ \t]*(?:export[ \t]+(?:default[ \t]+)?)?(?:async[ \t]+)?function\b"
    r"|^[ \t]*(?:export[ \t]+(?:default[ \t]+)?)?class\b"
    r"|^[ \t]*(?:export[ \t]+)?(?:const|let|var)[ \t]+[\w$]+[ \t]*=[ \t]*"
    r"(?:async[ \t]*)?(?:function\b|\([^)\n]*\)[ \t]*=>|[\w$]+[ \t]*=>)" + _JS_METHOD
)

#: JavaScript's, plus interfaces, enums, namespaces and type aliases.
TYPESCRIPT = (
    JAVASCRIPT + r"|^[ \t]*(?:export[ \t]+)?(?:declare[ \t]+)?(?:abstract[ \t]+)?"
    r"(?:interface|enum|namespace|module|class)[ \t]+\w"
    r"|^[ \t]*(?:export[ \t]+)?type[ \t]+\w+[ \t]*(?:<[^>\n]*>)?[ \t]*="
)

PYTHON = r"^[ \t]*(?:@[\w.]+.*\n[ \t]*)*(?:async[ \t]+def|def|class)[ \t]+\w"

#: Headings, the landmark elements, and anything carrying a landmark role.
HTML = (
    r"(?i)^[ \t]*<(?:h[1-6]|main|nav|header|footer|aside|section|article|form)\b"
    r"|^[ \t]*<\w+[^>\n]*\brole[ \t]*=[ \t]*[\"']?"
    r"(?:banner|navigation|main|contentinfo|complementary|search|region|form)\b"
)

#: ``[section]`` in INI and TOML, and TOML's ``[[array.of.tables]]``.
SECTIONS = r"^[ \t]*\[\[?[^\]\n]+\]\]?[ \t]*(?:[#;].*)?$"

#: ``:label`` -- but not ``::``, which is a comment.
BATCH = r"^[ \t]*:(?!:)[^\s:]"

LATEX = (
    r"^[ \t]*\\(?:part|chapter|section|subsection|subsubsection|paragraph)\*?"
    r"[ \t]*[\[{]"
)

GO = r"^(?:func|type)[ \t]"

RUST = (
    r"^[ \t]*(?:pub(?:\([^)\n]*\))?[ \t]+)?(?:(?:async|unsafe|const)[ \t]+)*"
    r"(?:fn|struct|enum|trait|impl|mod)\b"
)

KOTLIN = (
    r"^[ \t]*(?:(?:public|private|protected|internal|open|abstract|override|"
    r"suspend|data|sealed|inline|enum|inner)[ \t]+)*(?:fun|class|object|interface)[ \t]+"
)

PHP = (
    r"^[ \t]*(?:(?:public|private|protected|static|abstract|final)[ \t]+)*"
    r"(?:function|class|interface|trait|enum)[ \t]+\w"
)

#: ``name() {`` and ``function name``.
SHELL = r"^[ \t]*(?:function[ \t]+[\w-]+|[\w-]+[ \t]*\(\))"

POWERSHELL = r"(?i)^[ \t]*(?:function|filter|class|workflow)[ \t]+[\w-]+"

#: A definition at the left margin: a name, then an open parenthesis, on a line
#: that does not end in a semicolon; and class, struct and namespace blocks.
C_LIKE = (
    r"^(?!(?:if|for|while|switch|return|else|do|typedef|#)\b)"
    r"[A-Za-z_][\w \t\*&:<>,~]*\((?![^\n]*;[ \t]*$)"
    r"|^[ \t]*(?:template[ \t]*<[^>\n]*>[ \t]*)?(?:class|struct|namespace|union|enum)[ \t]+\w"
    r"[^;\n]*$"
)

RUBY = r"^[ \t]*(?:def|class|module)[ \t]+"

PERL = r"^[ \t]*(?:sub|package)[ \t]+\w"

SQL = r"(?i)^[ \t]*(?:create|alter|drop)[ \t]+"

#: A rule set: a selector line that opens a brace, or an at-rule.
CSS = r"^[ \t]*(?:@[\w-]+|[^\s{}/*@][^{};\n]*)\{"
