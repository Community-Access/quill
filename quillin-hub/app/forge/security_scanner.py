import ast


class SecurityWatchdog:
    """
    Static Analysis Watchdog for Quillin extensions.
    Analyzes source code for security vulnerabilities and capability honesty.
    """

    # Banned modules that often indicate sandbox escape attempts. No manifest
    # capability grants raw process execution, so subprocess is an outright
    # ban rather than a capability-honesty check (same reasoning as ctypes).
    BANNED_MODULES = {
        "ctypes",
        "pickle",
        "marshal",
        "subprocess",
        "platformdirs",  # Use QUILL's internal API instead
    }

    # Dangerous calls that bypass static analysis outright, regardless of
    # capability declarations. Bare-name form (eval(...)) and attribute form
    # (os.system(...), subprocess.call(...)) are both checked.
    BANNED_CALLS = {"eval", "exec", "system", "popen"}

    # Modules that require at least one of the listed capabilities. Values
    # are tuples because the manifest schema (quill/core/schemas/extension.json)
    # uses granular ids like "fs.read"/"fs.write", not a bare "fs".
    CAPABILITY_MAP = {
        "os": ("fs.read", "fs.write"),
        "shutil": ("fs.read", "fs.write"),
        "glob": ("fs.read", "fs.write"),
        "requests": ("net",),
        "urllib": ("net",),
        "http": ("net",),
        "socket": ("net",),
    }

    def __init__(self, manifest):
        self.manifest = manifest
        self.declared_capabilities = set(manifest.get("capabilities", []))

    def scan_file(self, file_path: str) -> list[tuple[int, str]]:
        """
        Scans a python file using AST to find security and watchdog issues.
        Returns a list of (line_number, issue_message).
        """
        issues = []
        with open(file_path, encoding="utf-8") as f:
            try:
                tree = ast.parse(f.read())
            except SyntaxError as e:
                return [(e.lineno, f"Syntax Error: {e.msg}")]

        for node in ast.walk(tree):
            # Check for Imports
            if isinstance(node, ast.Import):
                for alias in node.names:
                    issue = self._check_module(alias.name, node.lineno)
                    if issue:
                        issues.append(issue)

            elif isinstance(node, ast.ImportFrom):
                issue = self._check_module(node.module, node.lineno)
                if issue:
                    issues.append(issue)

            # Check for dangerous function calls: eval/exec (bare name) and
            # os.system / os.popen / subprocess.call-style (attribute) calls.
            elif isinstance(node, ast.Call):
                called_name = None
                if isinstance(node.func, ast.Name):
                    called_name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    called_name = node.func.attr
                if called_name in self.BANNED_CALLS:
                    issues.append((
                        node.lineno,
                        f"CRITICAL: Forbidden use of {called_name}(). Sandbox escape risk.",
                    ))

        return issues

    def _check_module(self, module_name: str, line_no: int) -> tuple[int, str] | None:
        if not module_name:
            return None

        # 1. Check for outright banned modules
        if module_name in self.BANNED_MODULES:
            return (
                line_no,
                f"SECURITY: Use of banned module '{module_name}' is strictly forbidden.",
            )

        # 2. Check for capability honesty
        for mod, caps in self.CAPABILITY_MAP.items():
            if module_name == mod or module_name.startswith(f"{mod}."):
                if not self.declared_capabilities.intersection(caps):
                    return (
                        line_no,
                        f"WATCHDOG: Module '{module_name}' requires one of {sorted(caps)}"
                        " capability, none of which is declared in manifest.",
                    )

        return None
