"""Mint a pre-beta unlock code. Dev-only tool -- not bundled with QUILL.

One-time setup, run once and keep the private key somewhere safe (a
password manager, not this repo)::

    python -m quill.tools.signing keygen --pub quill/core/unlock-pub.key --priv unlock-priv.key

Commit ``quill/core/unlock-pub.key`` (a public key -- safe to ship). Never
commit ``unlock-priv.key``.

Then, to hand a trusted tester access to a locked feature::

    python -m quill.tools.mint_unlock_code --feature core.adp \\
        --secret-key unlock-priv.key --tester "Robert H." --expires 2027-01-01

Prints a code shaped like ``QUILL-XXXX-XXXX-...`` to paste to the tester;
they redeem it from QUILL's Help menu. No expiry is required -- omit
``--expires`` for a code that's valid indefinitely (still revocable in
spirit: mint a new keypair and ship the new public key to invalidate every
previously-issued code at once, if that's ever needed).
"""

from __future__ import annotations

import argparse
from pathlib import Path

from quill.core.unlock_codes import mint_code
from quill.tools.signing import load_secret_key


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m quill.tools.mint_unlock_code",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--feature", required=True, help="Feature id to unlock, e.g. core.adp.")
    parser.add_argument(
        "--secret-key", required=True, help="Path to the unlock signing private key."
    )
    parser.add_argument("--tester", default="", help="Optional tester name, for your own records.")
    parser.add_argument(
        "--expires", default=None, help="Optional expiry date, YYYY-MM-DD. Omit for no expiry."
    )
    args = parser.parse_args(argv)

    secret_key = load_secret_key(Path(args.secret_key))
    code = mint_code(args.feature, secret_key, expires=args.expires)
    # --tester is never signed into the code itself (it would only make the
    # code longer); it's echoed back here purely for Jeff's own records of
    # who a given code was handed to.
    if args.tester:
        print(f"# tester: {args.tester}")
    print(code)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
