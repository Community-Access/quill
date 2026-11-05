#!/usr/bin/env python
"""Copy the test site's passwords into Windows Credential Manager.

Reads the server's ``~/app/wordpress-test/test-accounts.txt`` over ssh and
stores each password with ``keyring`` (Windows Credential Manager on
Windows), where ``docs/qa/wordpress-live-run.py`` looks for them:

- service: ``QUILL WordPress test site (lp.csedesigns.com)``;
- user name: ``"<login> <kind>"``, where kind is ``sign-in`` or
  ``application`` (``"quill-editor application"``).

With ``--admin-sign-in`` it also stores quilladmin's sign-in password, read
from ``ADMIN_PASSWORD`` in the server's ``.env`` (only that one line is read).

It prints only the names it stored, never a value. Run it from the
repository root after the server's passwords change::

    python docs/qa/wordpress-test-site/store-passwords.py
    python docs/qa/wordpress-test-site/store-passwords.py --admin-sign-in
"""

from __future__ import annotations

import argparse
import importlib.util
import subprocess
import sys
from pathlib import Path

HOST = "lp.csedesigns.com"
ACCOUNTS_COMMAND = "cat app/wordpress-test/test-accounts.txt"
ADMIN_COMMAND = "sed -n 's/^ADMIN_PASSWORD=//p' app/wordpress-test/.env"
HARNESS = Path(__file__).resolve().parents[1] / "wordpress-live-run.py"


def _harness():
    """The live harness, for its one parser and its service name."""
    spec = importlib.util.spec_from_file_location("wordpress_live_run", HARNESS)
    if spec is None or spec.loader is None:
        raise SystemExit(f"Could not load {HARNESS}.")
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("wordpress_live_run", module)
    spec.loader.exec_module(module)
    return module


def entries_from(text: str, admin_sign_in: str = "") -> dict[tuple[str, str], str]:
    """``(login, kind) -> password`` from the accounts file, plus the admin's sign-in."""
    found = dict(_harness().parse_accounts(text))
    secret = admin_sign_in.strip().strip("'\"")
    if secret:
        found[("quilladmin", "sign-in")] = secret
    return found


def keyring_user(login: str, kind: str) -> str:
    return f"{login} {kind}"


def _ssh(command: str) -> str:
    result = subprocess.run(
        ["ssh", HOST, command], capture_output=True, text=True, encoding="utf-8", check=False
    )
    if result.returncode != 0:
        raise SystemExit(f"ssh {HOST} failed (exit {result.returncode}); nothing was stored.")
    return result.stdout


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Store the test site's passwords locally.")
    parser.add_argument(
        "--admin-sign-in",
        action="store_true",
        help="also store quilladmin's sign-in password from the server's .env",
    )
    parser.add_argument(
        "--file",
        type=Path,
        help="read a local copy of test-accounts.txt instead of using ssh",
    )
    args = parser.parse_args(argv)
    try:
        import keyring
    except ImportError:
        print("keyring is not installed (pip install keyring); nothing was stored.")
        return 1
    text = args.file.read_text(encoding="utf-8") if args.file else _ssh(ACCOUNTS_COMMAND)
    admin = _ssh(ADMIN_COMMAND) if args.admin_sign_in else ""
    found = entries_from(text, admin)
    if not found:
        print("No passwords were found in the accounts file; nothing was stored.")
        return 1
    service = _harness().SERVICE
    for (login, kind), secret in sorted(found.items()):
        keyring.set_password(service, keyring_user(login, kind), secret)
        print(f"Stored {keyring_user(login, kind)}")
    print(f"{len(found)} entries under '{service}'.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
