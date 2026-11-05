from pathlib import Path

TEXT_EXTENSIONS = {
    ".txt",
    ".md",
    ".markdown",
    ".rst",
    ".json",
    ".toml",
    ".yaml",
    ".yml",
    ".xml",
    ".csv",
    ".tsv",
    ".ini",
    ".cfg",
    ".log",
    ".py",
    ".html",
    ".htm",
    ".css",
    ".js",
    ".ts",
    # A form document (QUILL Accessible Forms, wordpress.md 17a.17): plain text.
    ".qaf",
}

STRUCTURED_EXTENSIONS = {
    ".pdf",
    ".pages",
    ".epub",
    ".doc",
    ".docx",
    ".ppt",
    ".xlsx",
    ".xls",
    ".pptx",
}


def looks_like_text(path: Path) -> bool:
    return path.suffix.lower() in TEXT_EXTENSIONS
