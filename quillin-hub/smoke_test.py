"""Smoke test for the Quillin Hub: routes, API, and real Forge submissions.

Runs against a throwaway SQLite database -- no PostgreSQL required. Needs the
Hub requirements installed plus the main QUILL package (``pip install -e ..``)
so the Forge can shell out to ``quill.tools.signing`` and
``quill.tools.artifact_validate``.

Usage::

    python smoke_test.py
"""

import base64
import io
import json
import os
import sys
import tempfile
import zipfile
from pathlib import Path

HUB_DIR = Path(__file__).resolve().parent
REPO = HUB_DIR.parent
sys.path.insert(0, str(HUB_DIR))
os.chdir(HUB_DIR)

tmp = tempfile.mkdtemp(prefix="hub-smoke-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(tmp, "hub.db").replace("\\", "/")

from app import create_app, db  # noqa: E402

# Generate a test keypair. The Hub linter shells out to
# `quill.tools.artifact_validate` as a subprocess; we set the public
# key via SIGNING_PUBLIC_KEY_PATH so both the parent process and the
# subprocess resolve to our test key.
from nacl import signing as nacl_signing  # noqa: E402

_test_sk = nacl_signing.SigningKey.generate()
_test_pub_b64 = base64.b64encode(bytes(_test_sk.verify_key)).decode()

# Write a temporary public key file the subprocess can load.
_test_pub_path = Path(tmp) / "smoke-pub.key"
_test_pub_path.write_text(_test_pub_b64 + "\n", encoding="utf-8")
os.environ["SIGNING_PUBLIC_KEY_PATH"] = str(_test_pub_path)

# Patch the in-process module so the parent's _read_bundled_public_key
# reads from the test key file. (PUBLIC_KEY_B64 was set at module import
# to the bundled real publisher key; we override it here.)
import quill.tools.signing as _signing_mod  # noqa: E402

_signing_mod.PUBLIC_KEY_B64 = _test_pub_b64
_signing_mod.load_publisher_public_key_from = (  # type: ignore[assignment]
    lambda _path: _test_sk.verify_key
)


def _sign_sidecar(artifact_path: Path) -> Path:
    """Sign the artifact and write a sidecar next to it. Returns sidecar."""
    sidecar = artifact_path.with_suffix(artifact_path.suffix + ".minisig")
    _signing_mod.sign_artifact(artifact_path, _test_sk)
    return sidecar


app = create_app()
app.config["UPLOAD_FOLDER"] = os.path.join(tmp, "uploads")
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

with app.app_context():
    db.create_all()
    from app.models.database import Artifact

    db.session.add(
        Artifact(
            manifest_id="agent:summarizer",
            artifact_type="agent",
            name="Summarizer",
            version="1.0.0",
            description="Summarizes documents.",
            status="Verified",
            download_url="https://example.test/summarizer.md",
            is_gold_standard=True,
        )
    )
    db.session.commit()

client = app.test_client()
checks = []


def check(name, ok, detail=""):
    checks.append((name, ok))
    print(("OK  " if ok else "FAIL") + " " + name + (" -- " + detail if detail and not ok else ""))


r = client.get("/")
check("storefront 200", r.status_code == 200)
check("storefront shows agent", b"Summarizer" in r.data)
check("storefront type filter nav", b"Browse by type" in r.data)

r = client.get("/?type=agent")
check("type filter 200", r.status_code == 200 and b"Summarizer" in r.data)

r = client.get("/?type=quillin")
check("empty type filter", r.status_code == 200 and b"Summarizer" not in r.data)

r = client.get("/artifact/1")
check("detail page 200", r.status_code == 200 and b"Summarizer" in r.data)

r = client.get("/plugin/1")
check("legacy plugin URL", r.status_code == 200)

r = client.get("/search?q=Summar")
check("search 200", r.status_code == 200 and b"Summarizer" in r.data)

r = client.get("/api/v1/types")
check("api types lists all 7", r.status_code == 200 and len(r.get_json()) == 7)

r = client.get("/api/v1/artifacts")
check("api artifacts", r.status_code == 200 and len(r.get_json()) == 1)

r = client.get("/api/v1/artifacts?type=agent")
check("api artifacts type filter", len(r.get_json()) == 1)

r = client.get("/api/v1/artifacts?type=bogus")
check("api artifacts bad type 400", r.status_code == 400)

r = client.get("/api/v1/plugins")
check("api legacy plugins quillin-only", r.status_code == 200 and r.get_json() == [])

r = client.get("/api/v1/artifacts/agent:summarizer/latest")
check("api latest", r.status_code == 200 and r.get_json()["version"] == "1.0.0")

r = client.get("/forge/")
check("forge index 200", r.status_code == 200 and b"What can you share?" in r.data)

r = client.get("/forge/submit")
check("forge submit form 200", r.status_code == 200)

# Real submissions through the Forge.
# 1. A pronunciation dictionary (pass).
pron = json.dumps({"id": "smoke", "name": "Smoke", "entries": [{"term": "QUILL"}]}).encode()
pron_path = Path(tmp) / "smoke-dict.json"
pron_path.write_bytes(pron)
_sign_sidecar(pron_path)
pron_sidecar = pron_path.with_suffix(pron_path.suffix + ".minisig")
r = client.post(
    "/forge/submit",
    data={
        "artifact": (pron_path.open("rb"), "smoke-dict.json"),
        "signature": (pron_sidecar.open("rb"), pron_sidecar.name),
    },
    content_type="multipart/form-data",
)
check(
    "forge pronunciation pass",
    r.status_code == 200 and b"Passed." in r.data,
    r.data[:300].decode("utf-8", "replace"),
)

# 2. A broken keyboard pack (fail).
bad_kqp = json.dumps({"name": "No version"}).encode()
bad_kqp_path = Path(tmp) / "bad.kqp"
bad_kqp_path.write_bytes(bad_kqp)
# Sign it -- the signature check runs first, before the validator, so
# an unsigned submission would fail with a different (signature) error
# than what this test asserts.
_sign_sidecar(bad_kqp_path)
bad_kqp_sidecar = bad_kqp_path.with_suffix(bad_kqp_path.suffix + ".minisig")
r = client.post(
    "/forge/submit",
    data={
        "artifact": (bad_kqp_path.open("rb"), "bad.kqp"),
        "signature": (bad_kqp_sidecar.open("rb"), bad_kqp_sidecar.name),
    },
    content_type="multipart/form-data",
)
check("forge bad kqp fails", r.status_code == 200 and b"Needs work." in r.data)

# 3. A zipped Quillin (a real bundled one).
quillin_dir = REPO / "quill" / "quillins_bundled" / "journal-stamp"
buffer = io.BytesIO()
with zipfile.ZipFile(buffer, "w") as archive:
    for path in quillin_dir.rglob("*"):
        if path.is_file():
            archive.write(path, str(path.relative_to(quillin_dir.parent)))
buffer.seek(0)
quillin_zip_path = Path(tmp) / "journal-stamp.zip"
quillin_zip_path.write_bytes(buffer.getvalue())
_sign_sidecar(quillin_zip_path)
quillin_sidecar = quillin_zip_path.with_suffix(quillin_zip_path.suffix + ".minisig")
r = client.post(
    "/forge/submit",
    data={
        "artifact": (quillin_zip_path.open("rb"), "journal-stamp.zip"),
        "signature": (quillin_sidecar.open("rb"), quillin_sidecar.name),
    },
    content_type="multipart/form-data",
)
check(
    "forge zipped quillin pass",
    r.status_code == 200 and b"Passed." in r.data,
    r.data[:500].decode("utf-8", "replace"),
)

# 4. A disallowed file type.
r = client.post(
    "/forge/submit",
    data={"artifact": (io.BytesIO(b"x"), "evil.exe")},
    content_type="multipart/form-data",
)
check("forge rejects unknown suffix", r.status_code == 400)

# 5. An unsigned submission must be rejected by the signature gate.
unsigned_path = Path(tmp) / "unsigned.kqp"
unsigned_path.write_bytes(json.dumps({"kqp_version": 1, "name": "u", "bindings": {}}).encode())
r = client.post(
    "/forge/submit",
    data={"artifact": (unsigned_path.open("rb"), "unsigned.kqp")},
    content_type="multipart/form-data",
)
check(
    "forge rejects unsigned submission",
    r.status_code == 200 and b"Unsigned" in r.data,
    r.data[:300].decode("utf-8", "replace"),
)

with app.app_context():
    from app.models.database import Submission

    count = Submission.query.count()
    check("submissions recorded", count == 4, f"count={count}")

failed = [name for name, ok in checks if not ok]
print()
print(f"{len(checks) - len(failed)}/{len(checks)} checks passed")
sys.exit(1 if failed else 0)
